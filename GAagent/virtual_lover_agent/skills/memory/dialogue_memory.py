import json
import logging
from dataclasses import dataclass
from urllib.parse import quote, unquote
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError, WatchError

from virtual_lover_agent.skills.memory.context import (
    COMPACTION_TURNS,
    RECENT_TURNS,
    ROLLING_SUMMARIES,
    Summarize,
    build_memory_context,
    history_budget,
    transcript_for,
)


logger = logging.getLogger(__name__)

DEFAULT_HISTORY_PREFIX = "vr:history:"
COMPANION_HISTORY_PREFIX = "vr:companion_history:"
LEGACY_ARCHIVE_QUEUE = "vr:long_term_queue"
COMPRESSION_THRESHOLD = RECENT_TURNS * 2
COMPRESSION_BATCH = COMPACTION_TURNS * 2
LEGACY_HISTORY_MESSAGES = 50


@dataclass(frozen=True)
class MemoryKeys:
    history: str
    summaries: str
    archive: str
    checkpoint: str

    @classmethod
    def for_user(cls, user_id: str, companion_id: str = "") -> "MemoryKeys":
        if companion_id in ("", "default"):
            return cls(
                DEFAULT_HISTORY_PREFIX + user_id,
                f"vr:summary:{user_id}",
                f"vr:long_term:{user_id}",
                f"vr:history_checkpoint:{user_id}",
            )
        scope = f"{quote(user_id, safe='')}:{quote(companion_id, safe='')}"
        return cls(
            COMPANION_HISTORY_PREFIX + scope,
            f"vr:companion_summary:{scope}",
            f"vr:companion_long_term:{scope}",
            f"vr:companion_history_checkpoint:{scope}",
        )

    @classmethod
    def from_history(cls, key: str) -> "MemoryKeys":
        if key.startswith(DEFAULT_HISTORY_PREFIX):
            return cls.for_user(key.removeprefix(DEFAULT_HISTORY_PREFIX))
        user_id, _, companion_id = key.removeprefix(COMPANION_HISTORY_PREFIX).partition(":")
        return cls.for_user(unquote(user_id), unquote(companion_id))


def _parse_message(row: str) -> tuple[str, str] | None:
    try:
        message = json.loads(row)
    except json.JSONDecodeError:
        message = row

    if isinstance(message, dict):
        role, content = message.get("role"), message.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            return role, content
    elif isinstance(message, str):
        # The previous Java and Python gateways wrote JSON strings and raw strings.
        role, _, content = message.partition(": ")
        if role == "User":
            return "user", content
        if role == "AI":
            return "assistant", content
    return None


class MemoryService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def recent_turn_messages(
        self, user_id: str, *, companion_id: str = ""
    ) -> list[tuple[str, str]]:
        keys = MemoryKeys.for_user(user_id, companion_id)
        rows = await self.redis.lrange(keys.history, -LEGACY_HISTORY_MESSAGES, -1)
        messages = []
        pending_user = None
        for row in rows:
            message = _parse_message(row)
            if message is None or not message[1].strip():
                pending_user = None
            elif message[0] == "user":
                pending_user = message
            elif pending_user is not None:
                messages.extend((pending_user, message))
                pending_user = None
        return messages[-COMPRESSION_THRESHOLD:]

    async def build_messages(
        self,
        user_id: str,
        system_prompt: str,
        user_text: str,
        *,
        companion_id: str = "",
    ) -> list[tuple[str, str]]:
        if history_budget(system_prompt, user_text) <= 0:
            return [("system", system_prompt), ("user", user_text)]

        keys = MemoryKeys.for_user(user_id, companion_id)
        try:
            async with self.redis.pipeline() as read:
                read.lrange(keys.history, -COMPRESSION_THRESHOLD, -1)
                read.lrange(keys.summaries, 0, -1)
                read.lrange(keys.archive, 0, -1)
                recent, summaries, archive = await read.execute()
        except RedisError:
            logger.warning("Dialogue memory unavailable while building model context")
            return [("system", system_prompt), ("user", user_text)]

        history = [message for row in recent if (message := _parse_message(row)) is not None]
        return build_memory_context(system_prompt, user_text, history, summaries, archive)

    async def save_turn(
        self,
        user_id: str,
        user_text: str,
        assistant_text: str,
        *,
        companion_id: str = "",
    ) -> None:
        if not user_id or not user_text.strip() or not assistant_text.strip():
            return
        keys = MemoryKeys.for_user(user_id, companion_id)
        rows = [
            json.dumps({"role": role, "content": content}, ensure_ascii=False)
            for role, content in (("user", user_text), ("assistant", assistant_text))
        ]
        async with self.redis.pipeline() as write:
            write.rpush(keys.history, *rows)
            write.persist(keys.history)
            await write.execute()

    async def run_compaction(self, summarize: Summarize) -> None:
        try:
            for _ in range(100):
                if not await self.archive_pending_summary():
                    break
            for prefix in (DEFAULT_HISTORY_PREFIX, COMPANION_HISTORY_PREFIX):
                async for key in self.redis.scan_iter(match=f"{prefix}*", count=100):
                    await self.compact(MemoryKeys.from_history(key), summarize)
        except RedisError as error:
            logger.warning("Redis unavailable to memory worker (%s)", type(error).__name__)

    async def compact(self, keys: MemoryKeys, summarize: Summarize) -> bool:
        async with self.redis.pipeline() as read:
            read.llen(keys.history)
            read.lrange(keys.history, 0, COMPRESSION_BATCH - 1)
            read.get(keys.checkpoint)
            length, oldest, checkpoint = await read.execute()
        if length <= COMPRESSION_THRESHOLD:
            return False

        turns = [message for row in oldest if (message := _parse_message(row)) is not None]
        if not turns:
            return False
        summary = (await summarize(transcript_for(turns))).strip()
        if not summary:
            return False
        return await self._commit_compaction(keys, oldest, summary, checkpoint)

    async def _commit_compaction(
        self, keys: MemoryKeys, oldest: list[str], summary: str, checkpoint: str | None
    ) -> bool:
        async with self.redis.pipeline() as write:
            try:
                await write.watch(keys.history, keys.summaries, keys.archive, keys.checkpoint)
                if await write.get(keys.checkpoint) != checkpoint:
                    return False
                if await write.lrange(keys.history, 0, len(oldest) - 1) != oldest:
                    return False
                recent = await write.lrange(keys.summaries, 0, -1)
                overflow = recent[:max(0, len(recent) + 1 - ROLLING_SUMMARIES)]
                has_summary = summary.upper() != "NO_INFO"
                if has_summary and overflow and await write.type(keys.archive) not in ("none", "list"):
                    raise RedisError("Dialogue archive key must contain a list")
                write.multi()
                if has_summary:
                    if overflow:
                        write.rpush(keys.archive, *overflow)
                        write.ltrim(keys.summaries, len(overflow), -1)
                    write.rpush(keys.summaries, summary)
                write.ltrim(keys.history, len(oldest), -1)
                write.persist(keys.history)
                write.set(keys.checkpoint, uuid4().hex)
                await write.execute()
            except WatchError:
                return False
        return True

    async def archive_pending_summary(self) -> bool:
        """Import one oldest entry from the prior worker's durable summary queue."""
        async with self.redis.pipeline() as write:
            try:
                await write.watch(LEGACY_ARCHIVE_QUEUE)
                entry = await write.lindex(LEGACY_ARCHIVE_QUEUE, -1)
                if entry is None:
                    return False
                try:
                    record = json.loads(entry)
                    user_id = record["user_id"]
                    summary = record["summary"]
                    valid = (
                        isinstance(user_id, str)
                        and bool(user_id)
                        and isinstance(summary, str)
                        and bool(summary.strip())
                    )
                except (json.JSONDecodeError, KeyError, TypeError):
                    valid = False

                if valid:
                    destination = MemoryKeys.for_user(user_id).archive
                    summary = summary.strip()
                else:
                    destination = f"{LEGACY_ARCHIVE_QUEUE}:invalid"
                    summary = entry
                    logger.warning("Moved a malformed legacy memory item to the invalid queue")
                await write.watch(destination)
                if await write.type(destination) not in ("none", "list"):
                    raise RedisError("Legacy memory destination key must contain a list")
                write.multi()
                write.rpush(destination, summary)
                write.rpop(LEGACY_ARCHIVE_QUEUE)
                await write.execute()
            except WatchError:
                return False
        return True
