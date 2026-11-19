import asyncio
import base64
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, aclosing
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, ValidationError
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect

from virtual_lover_agent.app.dialogue import MAX_MESSAGE_LENGTH, Companion, DialogueError
from virtual_lover_agent.app.runtime import Runtime
from virtual_lover_agent.app.voice import MAX_AUDIO_BYTES, VoiceError, VoiceReply, VoiceService

bearer = HTTPBearer(auto_error=False)
MAX_CHAT_BODY_BYTES = MAX_MESSAGE_LENGTH * 12 + 1024


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class VoiceOutput(BaseModel):
    user_text: str
    text: str
    audio_base64: str
    audio_content_type: str


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryOutput(BaseModel):
    messages: list[HistoryMessage]


def sse(event: dict[str, str]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def read_body(request: Request, limit: int, error_code: str) -> bytes:
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > limit:
                raise HTTPException(413, error_code)
            body.extend(chunk)
    except ClientDisconnect as exc:
        raise HTTPException(499, "client_disconnected") from exc
    return bytes(body)


async def respond_to_audio(request: Request, voice: VoiceService, companion: Companion, audio: bytes) -> VoiceReply:
    async def wait_for_disconnect() -> None:
        while (await request.receive())["type"] != "http.disconnect":
            pass

    reply = asyncio.create_task(voice.respond(companion, audio))
    disconnect = asyncio.create_task(wait_for_disconnect())
    try:
        done, _ = await asyncio.wait((reply, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if reply not in done:
            disconnect.result()
            raise ClientDisconnect()
        return reply.result()
    finally:
        reply.cancel()
        disconnect.cancel()
        await asyncio.gather(reply, disconnect, return_exceptions=True)


def current_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


def access_token(
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if credential is None:
        raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
    return credential.credentials


def make_http_app(
    *,
    title: str,
    mode: str,
    http_origins: tuple[str, ...],
    auth_configured: bool,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]],
    resolve_companion: Callable[..., Awaitable[Companion]],
) -> FastAPI:
    app = FastAPI(title=title, version="1.0", lifespan=lifespan)
    if http_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=list(http_origins),
            allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/health/live")
    async def live():
        return {"status": "up"}

    @app.get("/health/ready")
    async def ready(runtime: Annotated[Runtime, Depends(current_runtime)]):
        try:
            async with asyncio.timeout(3):
                if not await runtime.memory_ping():
                    raise RuntimeError("Memory storage did not respond to ping")
        except Exception:
            raise HTTPException(503, "memory_unavailable") from None
        return {"status": "ready", "voice_enabled": runtime.voice.enabled,
                "mode": mode, "mobile_auth_configured": auth_configured}

    @app.get("/v1/chat/history")
    async def chat_history(
        companion: Annotated[Companion, Depends(resolve_companion)],
        runtime: Annotated[Runtime, Depends(current_runtime)],
    ) -> HistoryOutput:
        try:
            messages = await runtime.dialogue.recent_turn_messages(companion)
        except DialogueError as exc:
            raise HTTPException(503, str(exc)) from exc
        return HistoryOutput(messages=[HistoryMessage(role=role, content=content) for role, content in messages])

    @app.post("/v1/chat/stream", responses={200: {"content": {"text/event-stream": {}}}},
              response_class=StreamingResponse, openapi_extra={"requestBody": {"required": True, "content": {
                  "application/json": {"schema": ChatInput.model_json_schema()},
              }}})
    async def chat(
        request: Request,
        companion: Annotated[Companion, Depends(resolve_companion)],
        runtime: Annotated[Runtime, Depends(current_runtime)],
    ):
        raw = await read_body(request, MAX_CHAT_BODY_BYTES, "message_too_large")
        try:
            payload = ChatInput.model_validate_json(raw)
        except ValidationError as exc:
            raise HTTPException(422, "invalid_message") from exc
        if not payload.message.strip():
            raise HTTPException(422, "invalid_message")

        async def generate() -> AsyncGenerator[str, None]:
            try:
                async with aclosing(runtime.dialogue.stream(companion, payload.message)) as events:
                    async for event in events:
                        if event.delta:
                            yield sse({"type": "delta", "delta": event.delta})
                        elif event.tool:
                            yield sse({"type": "tool", "name": event.tool})
                yield sse({"type": "done"})
            except DialogueError as exc:
                yield sse({"type": "error", "error": str(exc)})

        events = generate()
        return StreamingResponse(events, media_type="text/event-stream", background=BackgroundTask(events.aclose),
                                 headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"})

    @app.post("/v1/voice", openapi_extra={"requestBody": {"required": True, "content": {
        "audio/wav": {"schema": {"type": "string", "format": "binary"}},
    }}})
    async def voice(
        request: Request,
        companion: Annotated[Companion, Depends(resolve_companion)],
        runtime: Annotated[Runtime, Depends(current_runtime)],
    ) -> VoiceOutput:
        if request.headers.get("content-type", "").partition(";")[0].strip().lower() != "audio/wav":
            raise HTTPException(415, "expected_audio_wav")
        audio = await read_body(request, MAX_AUDIO_BYTES, "audio_too_large")
        try:
            reply = await respond_to_audio(request, runtime.voice, companion, audio)
        except ClientDisconnect as exc:
            raise HTTPException(499, "client_disconnected") from exc
        except (DialogueError, VoiceError) as exc:
            status = {"audio_too_large": 413, "invalid_audio": 422, "speech_not_recognized": 422,
                      "invalid_message": 422, "voice_disabled": 503, "memory_unavailable": 503}.get(str(exc), 502)
            raise HTTPException(status, str(exc)) from exc
        return VoiceOutput(
            user_text=reply.user_text, text=reply.text,
            audio_base64=base64.b64encode(reply.audio).decode("ascii"), audio_content_type=reply.content_type,
        )

    return app
