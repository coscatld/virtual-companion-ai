import base64
import io
import logging
import math
import struct
import wave
from contextlib import aclosing
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from virtual_lover_agent.app.config import InferenceSettings, ProviderSettings
from virtual_lover_agent.app.dialogue import Companion, DialogueService

logger = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_SECONDS = 60


class VoiceError(Exception):
    pass


@dataclass(frozen=True)
class VoiceReply:
    user_text: str
    text: str
    audio: bytes
    content_type: str


def validate_wav(audio: bytes) -> None:
    if len(audio) > MAX_AUDIO_BYTES:
        raise VoiceError("audio_too_large")
    try:
        with wave.open(io.BytesIO(audio), "rb") as recording:
            rate = recording.getframerate()
            frames = recording.getnframes()
            if recording.getnchannels() != 1 or recording.getsampwidth() != 2 or not 8_000 <= rate <= 48_000:
                raise VoiceError("invalid_audio")
            if frames > rate * MAX_AUDIO_SECONDS:
                raise VoiceError("audio_too_large")
            if frames == 0 or len(recording.readframes(frames)) != frames * 2:
                raise VoiceError("invalid_audio")
    except (wave.Error, EOFError, struct.error) as exc:
        raise VoiceError("invalid_audio") from exc


def provider_headers(provider: ProviderSettings) -> dict[str, str]:
    return {"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}


class VoiceService:
    def __init__(self, settings: InferenceSettings, client: httpx.AsyncClient, dialogue: DialogueService):
        self.asr = settings.asr
        self.tts = settings.tts
        self.tts_voice = settings.tts_voice
        self.client = client
        self.dialogue = dialogue

        for name, provider, choices in (
            ("ASR", self.asr, {"disabled", "qwen-omni", "openai", "mock"}),
            ("TTS", self.tts, {"disabled", "openai", "edge", "mock"}),
        ):
            if provider.kind not in choices:
                raise ValueError(f"Unknown GA_{name}_PROVIDER: {provider.kind}")
            if provider.kind in {"qwen-omni", "openai"} and not (provider.base_url and provider.model):
                raise ValueError(f"GA_{name}_BASE_URL and GA_{name}_MODEL are required for {provider.kind}")

        self.omni = None
        if self.asr.kind == "qwen-omni":
            self.omni = AsyncOpenAI(
                api_key=self.asr.api_key or "not-needed", base_url=self.asr.base_url,
                http_client=client, max_retries=1,
            )

    @property
    def enabled(self) -> bool:
        return self.asr.kind != "disabled" and self.tts.kind != "disabled"

    async def respond(self, companion: Companion, audio: bytes) -> VoiceReply:
        if not self.enabled:
            raise VoiceError("voice_disabled")
        validate_wav(audio)

        try:
            user_text = (await self.transcribe(audio)).strip()
        except Exception as exc:
            logger.warning("Speech recognition failed (%s)", type(exc).__name__)
            raise VoiceError("recognition_unavailable") from exc
        if not user_text:
            raise VoiceError("speech_not_recognized")

        async with aclosing(self.dialogue.stream(companion, user_text, remember=False)) as events:
            reply_text = "".join([event.delta async for event in events]).strip()

        try:
            spoken, content_type = await self.synthesize(reply_text, companion.voice_id)
        except VoiceError:
            raise
        except Exception as exc:
            logger.warning("Speech synthesis failed (%s)", type(exc).__name__)
            raise VoiceError("synthesis_unavailable") from exc
        if not spoken:
            raise VoiceError("synthesis_unavailable")
        await self.dialogue.save_turn(companion, user_text, reply_text)
        return VoiceReply(user_text, reply_text, spoken, content_type)

    async def transcribe(self, audio: bytes) -> str:
        if self.asr.kind == "mock":
            return "本地演示语音"

        if self.omni is not None:
            data = base64.b64encode(audio).decode("ascii")
            model_options = {"enable_thinking": False}
            if self.asr.model.startswith("qwen3.8-omni"):
                model_options = {"reasoning_effort": "none"}
            stream = await self.omni.chat.completions.create(
                model=self.asr.model,
                messages=[{"role": "user", "content": [
                    {"type": "input_audio", "input_audio": {"data": f"data:audio/wav;base64,{data}", "format": "wav"}},
                    {"type": "text", "text": "Transcribe the speech verbatim in its original language. Output only the transcript. For no speech output <NO_SPEECH>."},
                ]}],
                modalities=["text"],
                stream=True,
                max_tokens=1024,
                extra_body=model_options,
            )
            parts = []
            finish_reason = None
            async with stream:
                async for event in stream:
                    if not event.choices:
                        continue
                    choice = event.choices[0]
                    if choice.delta.content:
                        parts.append(choice.delta.content)
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
            if finish_reason != "stop":
                raise VoiceError("recognition_unavailable")
            transcript = "".join(parts).strip()
            return "" if transcript.upper() == "<NO_SPEECH>" else transcript

        response = await self.client.post(
            f"{self.asr.base_url.rstrip('/')}/audio/transcriptions",
            headers=provider_headers(self.asr),
            data={"model": self.asr.model, "response_format": "json"},
            files={"file": ("speech.wav", audio, "audio/wav")},
        )
        response.raise_for_status()
        return response.json()["text"]

    async def synthesize(self, text: str, voice_id: str) -> tuple[bytes, str]:
        if self.tts.kind == "mock":
            sample_rate = 16_000
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as recording:
                recording.setparams((1, 2, sample_rate, 0, "NONE", "not compressed"))
                tone = b"".join(
                    struct.pack("<h", int(1200 * math.sin(math.tau * 440 * sample / sample_rate)))
                    for sample in range(sample_rate // 3)
                )
                recording.writeframes(tone)
            return buffer.getvalue(), "audio/wav"

        output = bytearray()
        if self.tts.kind == "edge":
            from edge_tts import Communicate

            communicator = Communicate(text, voice_id or self.tts_voice or "zh-CN-XiaoxiaoNeural")
            async with aclosing(communicator.stream()) as events:
                async for event in events:
                    if event["type"] == "audio":
                        append_audio(output, event["data"])
            return bytes(output), "audio/mpeg"

        async with self.client.stream(
            "POST", f"{self.tts.base_url.rstrip('/')}/audio/speech",
            headers=provider_headers(self.tts),
            json={"model": self.tts.model, "input": text, "voice": voice_id or self.tts_voice or "vivian",
                  "response_format": "wav"},
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                append_audio(output, chunk)
        try:
            with wave.open(io.BytesIO(output), "rb") as recording:
                frames = recording.getnframes()
                frame_size = recording.getnchannels() * recording.getsampwidth()
                if not frames or len(recording.readframes(frames)) != frames * frame_size:
                    raise VoiceError("synthesis_unavailable")
        except (wave.Error, EOFError, struct.error) as exc:
            raise VoiceError("synthesis_unavailable") from exc
        return bytes(output), "audio/wav"


def append_audio(buffer: bytearray, audio: bytes) -> None:
    if len(buffer) + len(audio) > MAX_AUDIO_BYTES:
        raise VoiceError("audio_reply_too_large")
    buffer.extend(audio)
