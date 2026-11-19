from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from virtual_lover_agent.app.memory_summarizer import memory_pruning_worker, mock_summary
from virtual_lover_agent.app.runtime import Runtime, open_inference_runtime
from virtual_lover_agent.enterprise.config import EnterpriseSettings
from virtual_lover_agent.skills.memory.dialogue_memory import MemoryService


@asynccontextmanager
async def open_enterprise_runtime(settings: EnterpriseSettings) -> AsyncIterator[Runtime]:
    async with redis_client(settings) as redis:
        async with open_inference_runtime(settings, MemoryService(redis), redis.ping) as runtime:
            yield runtime


def redis_client(settings: EnterpriseSettings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=3)


async def compact_enterprise_memory() -> None:
    settings = EnterpriseSettings.from_env()
    async with redis_client(settings) as redis:
        await memory_pruning_worker(
            MemoryService(redis),
            summarize=mock_summary if settings.llm.kind == "mock" else None,
            summary_settings=settings.summary,
        )
