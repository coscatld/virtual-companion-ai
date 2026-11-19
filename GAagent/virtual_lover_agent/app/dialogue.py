import logging
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import dataclass
from typing import Protocol

from virtual_lover_agent.app.config import ProviderSettings

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 12_000
DEFAULT_PROMPT = "你是一位友善、体贴的 AI 伴侣。使用用户选择的语言自然地交流。"


class DialogueError(Exception):
    pass


class DialogueMemory(Protocol):
    async def build_messages(self, user_id: str, system_prompt: str, user_text: str,
                             *, companion_id: str) -> list[tuple[str, str]]: ...

    async def save_turn(self, user_id: str, user_text: str, assistant_text: str,
                        *, companion_id: str) -> None: ...

    async def recent_turn_messages(self, user_id: str, *, companion_id: str) -> list[tuple[str, str]]: ...


@dataclass(frozen=True)
class Companion:
    user_id: str
    companion_id: str = "default"
    system_prompt: str = DEFAULT_PROMPT
    voice_id: str = ""


@dataclass(frozen=True)
class DialogueEvent:
    delta: str = ""
    tool: str = ""


class DialogueModel(Protocol):
    def stream(self, messages: list[tuple[str, str]], *, user_text: str) -> AsyncGenerator[DialogueEvent, None]: ...


class GraphDialogueModel:
    def __init__(self, graph):
        self.graph = graph

    async def stream(self, messages: list[tuple[str, str]], *, user_text: str) -> AsyncGenerator[DialogueEvent, None]:
        finish_reason = None
        async with aclosing(self.graph.astream_events({"messages": messages}, version="v2")) as events:
            async for event in events:
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if isinstance(content, list):
                        content = "".join(
                            block.get("text", "") for block in content
                            if isinstance(block, dict) and block.get("type") == "text"
                            and isinstance(block.get("text"), str)
                        )
                    if content:
                        yield DialogueEvent(delta=content)
                elif event["event"] == "on_chat_model_end":
                    finish_reason = event["data"]["output"].response_metadata.get("finish_reason")
                elif event["event"] == "on_tool_start":
                    yield DialogueEvent(tool=event["name"])
        if finish_reason != "stop":
            raise DialogueError("incomplete_reply")


class MockDialogueModel:
    async def stream(self, messages: list[tuple[str, str]], *, user_text: str) -> AsyncGenerator[DialogueEvent, None]:
        yield DialogueEvent(delta="[本地演示] 收到：")
        yield DialogueEvent(delta=user_text[:200])


def create_dialogue_model(settings: ProviderSettings, *, public_tools: bool) -> DialogueModel:
    if settings.kind == "mock":
        return MockDialogueModel()
    if settings.kind == "openai":
        from virtual_lover_agent.agent.graph.gragh01 import create_agent

        return GraphDialogueModel(create_agent(settings, public_tools=public_tools))
    raise ValueError(f"Unknown GA_LLM_PROVIDER: {settings.kind}")


class DialogueService:
    def __init__(self, model: DialogueModel, memory: DialogueMemory):
        self.model = model
        self.memory = memory

    async def stream(self, companion: Companion, user_text: str, *,
                     remember: bool = True) -> AsyncGenerator[DialogueEvent, None]:
        if len(user_text) > MAX_MESSAGE_LENGTH or not user_text.strip():
            raise DialogueError("invalid_message")
        user_text = user_text.strip()
        try:
            user_text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise DialogueError("invalid_message") from exc

        try:
            messages = await self.memory.build_messages(
                companion.user_id, companion.system_prompt or DEFAULT_PROMPT, user_text,
                companion_id=companion.companion_id,
            )
        except Exception as exc:
            logger.warning("Dialogue memory read failed (%s)", type(exc).__name__)
            raise DialogueError("memory_unavailable") from exc

        reply = []
        try:
            async with aclosing(self.model.stream(messages, user_text=user_text)) as events:
                async for event in events:
                    if event.delta:
                        reply.append(event.delta)
                    yield event
        except DialogueError:
            raise
        except Exception as exc:
            logger.warning("Dialogue generation failed (%s)", type(exc).__name__)
            raise DialogueError("model_unavailable") from exc

        assistant_text = "".join(reply).strip()
        if not assistant_text:
            raise DialogueError("empty_reply")
        if remember:
            await self.save_turn(companion, user_text, assistant_text)

    async def save_turn(self, companion: Companion, user_text: str, assistant_text: str) -> None:
        try:
            await self.memory.save_turn(
                companion.user_id, user_text, assistant_text, companion_id=companion.companion_id,
            )
        except Exception as exc:
            logger.warning("Dialogue memory write failed (%s)", type(exc).__name__)
            raise DialogueError("memory_unavailable") from exc

    async def recent_turn_messages(self, companion: Companion) -> list[tuple[str, str]]:
        try:
            return await self.memory.recent_turn_messages(companion.user_id, companion_id=companion.companion_id)
        except Exception as exc:
            logger.warning("Dialogue history read failed (%s)", type(exc).__name__)
            raise DialogueError("memory_unavailable") from exc
