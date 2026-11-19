import asyncio
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing, suppress

import grpc

from virtual_lover_agent.app.dialogue import DEFAULT_PROMPT, Companion, DialogueError, DialogueService
from virtual_lover_agent.app.runtime import Runtime
from virtual_lover_agent.app.voice import MAX_AUDIO_BYTES, VoiceError, VoiceService
from virtual_lover_agent.enterprise.config import EnterpriseSettings
from virtual_lover_agent.enterprise.runtime import open_enterprise_runtime
from virtual_lover_agent.protos import agent_proto_pb2 as proto
from virtual_lover_agent.protos import agent_proto_pb2_grpc as services

logger = logging.getLogger(__name__)
GRPC_MESSAGE_BYTES = MAX_AUDIO_BYTES + 1024 * 1024


async def authorize(context: grpc.aio.ServicerContext, expected: str) -> None:
    if not expected:
        return
    tokens = [value for key, value in context.invocation_metadata() if key == "x-ga-internal-token"]
    if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode("utf-8"), expected.encode("utf-8")):
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid service credentials")


class AgentService(services.AgentServiceServicer):
    def __init__(self, dialogue: DialogueService, internal_token: str):
        self.dialogue = dialogue
        self.internal_token = internal_token

    async def chatStream(self, request: proto.ChatRequest,
                         context: grpc.aio.ServicerContext) -> AsyncIterator[proto.ChatResponse]:
        await authorize(context, self.internal_token)
        if not request.user_id.strip():
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "A user ID is required")

        companion = Companion(
            request.user_id, request.companion_id or "default", request.system_prompt or DEFAULT_PROMPT,
        )
        try:
            async with aclosing(self.dialogue.stream(
                companion, request.user_message, remember=not request.skip_memory_write,
            )) as events:
                async for event in events:
                    if event.delta:
                        yield proto.ChatResponse(delta=event.delta, emotion="normal")
                    elif event.tool:
                        yield proto.ChatResponse(emotion="thinking")
            yield proto.ChatResponse(emotion="done", is_end=True)
        except DialogueError as exc:
            yield proto.ChatResponse(delta=str(exc), emotion="error", is_end=True)

    async def GetRecentTurns(self, request: proto.RecentTurnsRequest,
                             context: grpc.aio.ServicerContext) -> proto.RecentTurnsResponse:
        await authorize(context, self.internal_token)
        if not request.user_id.strip():
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "A user ID is required")

        companion = Companion(request.user_id, request.companion_id or "default")
        try:
            messages = await self.dialogue.recent_turn_messages(companion)
        except DialogueError:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Dialogue history is unavailable")
        return proto.RecentTurnsResponse(messages=[
            proto.HistoryMessage(role=role, content=content) for role, content in messages
        ])


class AudioService(services.AudioServiceServicer):
    def __init__(self, voice: VoiceService, internal_token: str):
        self.voice = voice
        self.internal_token = internal_token

    async def StreamAudioChat(self, request_iterator: AsyncIterator[proto.AudioRequest],
                              context: grpc.aio.ServicerContext) -> AsyncIterator[proto.AudioResponse]:
        await authorize(context, self.internal_token)
        companion = None
        session_id = ""
        buffer = bytearray()
        overflow = False
        async for request in request_iterator:
            if companion is None:
                if not request.user_id and not request.audio_chunk:
                    continue
                if not request.user_id.strip():
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "A user ID is required")
                companion = Companion(
                    request.user_id, request.companion_id or "default",
                    request.system_prompt or DEFAULT_PROMPT, request.voice_id,
                )
                session_id = request.session_id
            elif any(
                incoming and incoming != bound for incoming, bound in (
                    (request.user_id, companion.user_id), (request.companion_id, companion.companion_id),
                    (request.session_id, session_id), (request.system_prompt, companion.system_prompt),
                    (request.voice_id, companion.voice_id),
                )
            ):
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Audio stream identity or profile changed")

            if request.audio_chunk:
                if not overflow and len(buffer) + len(request.audio_chunk) <= MAX_AUDIO_BYTES:
                    buffer.extend(request.audio_chunk)
                else:
                    overflow = True
                    buffer.clear()
                continue

            if overflow:
                overflow = False
                yield proto.AudioResponse(error="audio_too_large", is_end=True)
                continue
            if not buffer:
                continue

            audio = bytes(buffer)
            buffer.clear()
            try:
                reply = await self.voice.respond(companion, audio)
                yield proto.AudioResponse(
                    ai_audio_chunk=reply.audio, ai_text=reply.text, user_text=reply.user_text,
                    audio_content_type=reply.content_type, is_end=True,
                )
            except (DialogueError, VoiceError) as exc:
                yield proto.AudioResponse(error=str(exc), is_end=True)


async def start_grpc(runtime: Runtime, settings: EnterpriseSettings) -> grpc.aio.Server:
    if settings.mode != "enterprise":
        raise ValueError("The gRPC service requires enterprise mode")
    host = settings.grpc_bind.rsplit(":", 1)[0]
    if host not in {"127.0.0.1", "localhost", "[::1]"} and not settings.internal_token:
        raise ValueError("GA_INTERNAL_TOKEN is required when gRPC listens outside loopback")

    server = grpc.aio.server(options=(
        ("grpc.max_send_message_length", GRPC_MESSAGE_BYTES),
        ("grpc.max_receive_message_length", GRPC_MESSAGE_BYTES),
    ))
    services.add_AgentServiceServicer_to_server(AgentService(runtime.dialogue, settings.internal_token), server)
    services.add_AudioServiceServicer_to_server(AudioService(runtime.voice, settings.internal_token), server)
    server.add_insecure_port(settings.grpc_bind)
    await server.start()
    logger.info("gRPC agent listening on %s", settings.grpc_bind)
    return server


async def serve(settings: EnterpriseSettings) -> None:
    async with open_enterprise_runtime(settings) as runtime:
        server = await start_grpc(runtime, settings)
        try:
            await server.wait_for_termination()
        finally:
            await server.stop(3)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with suppress(KeyboardInterrupt):
        try:
            settings = EnterpriseSettings.from_env()
        except ValueError as exc:
            raise SystemExit(str(exc)) from None
        asyncio.run(serve(settings))
