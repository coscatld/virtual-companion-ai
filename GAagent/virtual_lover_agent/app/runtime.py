import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Protocol, TYPE_CHECKING

import httpx

from virtual_lover_agent.app.config import InferenceSettings
from virtual_lover_agent.app.dialogue import DialogueMemory, DialogueService, create_dialogue_model
from virtual_lover_agent.app.memory_summarizer import memory_pruning_worker, mock_summary
from virtual_lover_agent.app.voice import VoiceService
from virtual_lover_agent.skills.memory.context import CompactionStore

if TYPE_CHECKING:
    from virtual_lover_agent.enterprise.config import EnterpriseSettings
    from virtual_lover_agent.personal.config import PersonalSettings


class RuntimeMemory(DialogueMemory, CompactionStore, Protocol):
    pass


@dataclass
class Runtime:
    http: httpx.AsyncClient
    dialogue: DialogueService
    voice: VoiceService
    memory_ping: Callable[[], Awaitable[bool]]


@asynccontextmanager
async def open_inference_runtime(
    settings: InferenceSettings, memory: RuntimeMemory, memory_ping: Callable[[], Awaitable[bool]],
) -> AsyncIterator[Runtime]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=5)) as http:
        dialogue = DialogueService(create_dialogue_model(settings.llm, public_tools=settings.public_tools), memory)
        voice = VoiceService(settings, http, dialogue)
        worker = asyncio.create_task(memory_pruning_worker(
            memory_service=memory,
            summarize=mock_summary if settings.llm.kind == "mock" else None,
            summary_settings=settings.summary,
        ))
        try:
            yield Runtime(http, dialogue, voice, memory_ping)
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker


def open_runtime(settings: "EnterpriseSettings | PersonalSettings"):
    """Compatibility dispatcher. Product entry points open their own runtime directly."""
    if settings.mode == "personal":
        from virtual_lover_agent.personal.runtime import open_personal_runtime

        return open_personal_runtime(settings)
    from virtual_lover_agent.enterprise.runtime import open_enterprise_runtime

    return open_enterprise_runtime(settings)
