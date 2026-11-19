import asyncio
import json
import unittest
from unittest.mock import AsyncMock

try:
    from fakeredis import FakeAsyncRedis
except ImportError:
    FakeAsyncRedis = None

from virtual_lover_agent.skills.memory.bm25 import search_bm25
from virtual_lover_agent.skills.memory.dialogue_memory import (
    LEGACY_ARCHIVE_QUEUE,
    MemoryKeys,
    MemoryService,
)


class BM25Tests(unittest.TestCase):
    def test_ranks_chinese_and_english_and_excludes_zero_matches(self):
        documents = ["用户去过大阪", "用户养了一只布偶猫布丁", "The user likes jazz piano"]

        self.assertEqual(search_bm25("这只猫叫布丁吗", documents), [documents[1]])
        self.assertEqual(search_bm25("ＪＡＺＺ", documents), [documents[2]])
        self.assertEqual(search_bm25("气象天气", documents), [])


@unittest.skipIf(FakeAsyncRedis is None, "Install fakeredis to test Redis transactions")
class DialogueMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis = FakeAsyncRedis(decode_responses=True)
        self.addAsyncCleanup(self.redis.aclose)
        self.memory = MemoryService(self.redis)
        self.keys = MemoryKeys.for_user("user:1")

    async def add_turns(self, start, count):
        for turn in range(start, start + count):
            await self.memory.save_turn("user:1", f"message {turn}", f"reply {turn}")

    async def test_reads_legacy_java_and_python_history_and_adds_complete_turn(self):
        await self.redis.rpush(self.keys.history, json.dumps("User: earlier"), "AI: older reply")
        await self.redis.expire(self.keys.history, 60)
        await self.memory.save_turn("user:1", "later", "newer reply")

        self.assertEqual(
            await self.memory.build_messages("user:1", "fixed persona", "question"),
            [
                ("system", "fixed persona"),
                ("user", "earlier"),
                ("assistant", "older reply"),
                ("user", "later"),
                ("assistant", "newer reply"),
                ("user", "question"),
            ],
        )
        self.assertEqual(await self.redis.ttl(self.keys.history), -1)

    async def test_recent_turns_skip_incomplete_legacy_rows_and_stay_scoped(self):
        await self.add_turns(0, 11)
        await self.redis.rpush(
            self.keys.history,
            "AI: orphan reply",
            "User: abandoned",
            json.dumps("User: legacy question"),
            "AI: legacy reply",
            "User: interrupted",
            "unrecognized history row",
            "AI: no matching question",
            "User: unfinished",
        )
        await self.memory.save_turn("user:1", "another question", "another reply", companion_id="other")

        messages = await self.memory.recent_turn_messages("user:1")

        self.assertEqual(len(messages), 20)
        self.assertEqual(messages[0], ("user", "message 2"))
        self.assertEqual(messages[-2:], [("user", "legacy question"), ("assistant", "legacy reply")])
        self.assertEqual(await self.memory.recent_turn_messages("user:2"), [])
        self.assertEqual(
            await self.memory.recent_turn_messages("user:1", companion_id="other"),
            [("user", "another question"), ("assistant", "another reply")],
        )

    async def test_compacts_oldest_turns_and_promotes_summaries_into_user_scoped_archive(self):
        summaries = ["用户养了一只布偶猫布丁", "用户喝绿茶", "用户住青岛", "用户喜欢跑步", "用户上班坐地铁"]
        await self.add_turns(0, 8)
        for batch, summary in enumerate(summaries):
            await self.add_turns(8 + batch * 3, 3)
            summarize = AsyncMock(return_value=summary)
            self.assertTrue(await self.memory.compact(self.keys, summarize))
            self.assertTrue(summarize.call_args.args[0].startswith(f"user: message {batch * 3}\n"))

        self.assertEqual(await self.redis.lrange(self.keys.summaries, 0, -1), summaries[1:])
        self.assertEqual(await self.redis.lrange(self.keys.archive, 0, -1), summaries[:1])
        self.assertEqual(await self.redis.llen(self.keys.history), 16)

        query = "布丁是什么品种"
        recalled = await self.memory.build_messages("user:1", "persona", query)
        self.assertEqual(recalled[1], ("user", "message 15"))
        self.assertIn(summaries[0], recalled[-1][1])
        self.assertIn(summaries[-1], recalled[-1][1])

        for user_id, companion_id in (("user:2", ""), ("user:1", "another:companion")):
            self.assertEqual(
                await self.memory.build_messages(user_id, "persona", query, companion_id=companion_id),
                [("system", "persona"), ("user", query)],
            )

    async def test_bounds_historical_characters_without_trimming_the_current_query(self):
        await self.memory.save_turn("user:1", "猫" * 6_000, "天气" * 3_000)
        query = "旅行计划"

        messages = await self.memory.build_messages("user:1", "persona", query)

        self.assertEqual(messages[-1], ("user", query))
        self.assertEqual(len(messages[1][1]) + len(messages[2][1]), 8_000)
        self.assertTrue(messages[1][1].endswith("…"))

    async def test_failed_summary_keeps_turns_and_no_info_releases_them(self):
        await self.add_turns(0, 11)
        failing_summary = AsyncMock(side_effect=RuntimeError("model timeout"))

        with self.assertRaises(RuntimeError):
            await self.memory.compact(self.keys, failing_summary)
        self.assertEqual(await self.redis.llen(self.keys.history), 22)

        self.assertTrue(await self.memory.compact(self.keys, AsyncMock(return_value="NO_INFO")))
        self.assertEqual(await self.redis.llen(self.keys.history), 16)
        self.assertEqual(await self.redis.llen(self.keys.summaries), 0)

    async def test_competing_workers_commit_once_while_new_turn_remains(self):
        await self.redis.rpush(self.keys.history, *(["User: repeated", "AI: repeated reply"] * 11))
        release = asyncio.Event()
        both_summarizing = asyncio.Event()
        arrivals = 0

        async def summarize(transcript):
            nonlocal arrivals
            arrivals += 1
            if arrivals == 2:
                both_summarizing.set()
            await release.wait()
            return "Summary of competing snapshot"

        first = asyncio.create_task(self.memory.compact(self.keys, summarize))
        second = asyncio.create_task(self.memory.compact(self.keys, summarize))
        try:
            await asyncio.wait_for(both_summarizing.wait(), timeout=2)
            await self.add_turns(11, 1)
        finally:
            release.set()

        self.assertEqual(sum(await asyncio.gather(first, second)), 1)
        self.assertEqual(await self.redis.llen(self.keys.history), 18)
        self.assertEqual(await self.redis.llen(self.keys.summaries), 1)

    async def test_imports_legacy_archive_queue_and_preserves_malformed_entries(self):
        entry = json.dumps({"user_id": "user:1", "summary": "用户养了一只布偶猫布丁"})
        await self.redis.lpush(LEGACY_ARCHIVE_QUEUE, entry, "{}")

        self.assertTrue(await self.memory.archive_pending_summary())
        self.assertTrue(await self.memory.archive_pending_summary())
        self.assertFalse(await self.memory.archive_pending_summary())
        self.assertEqual(await self.redis.lrange(self.keys.archive, 0, -1), ["用户养了一只布偶猫布丁"])
        self.assertEqual(await self.redis.lrange(f"{LEGACY_ARCHIVE_QUEUE}:invalid", 0, -1), ["{}"])
