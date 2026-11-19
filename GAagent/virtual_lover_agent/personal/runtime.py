from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from virtual_lover_agent.app.runtime import Runtime, open_inference_runtime
from virtual_lover_agent.personal.config import PersonalSettings
from virtual_lover_agent.personal.profile import PersonalSettingsStore
from virtual_lover_agent.skills.memory.sqlite_memory import SQLiteMemoryService


@dataclass
class PersonalRuntime(Runtime):
    personal_settings: PersonalSettingsStore
    personal_token: str = field(repr=False)


@asynccontextmanager
async def open_personal_runtime(settings: PersonalSettings) -> AsyncIterator[PersonalRuntime]:
    store = PersonalSettingsStore(settings)
    token = await store.initialize()
    memory = SQLiteMemoryService(store.path)
    await memory.initialize()

    async with open_inference_runtime(settings, memory, memory.ping) as runtime:
        yield PersonalRuntime(runtime.http, runtime.dialogue, runtime.voice, runtime.memory_ping, store, token)
