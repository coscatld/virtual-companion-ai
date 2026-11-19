import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from virtual_lover_agent.skills.memory.sqlite_memory import SQLiteMemoryService


class SQLiteMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "personal data" / "ga.sqlite3"
        self.memory = SQLiteMemoryService(self.path)
        await self.memory.initialize()

    async def add_turns(self, start, count):
        for turn in range(start, start + count):
            await self.memory.save_turn("user", f"message {turn}", f"reply {turn}")

    async def test_persists_and_restores_chronological_scoped_turns(self):
        await self.add_turns(0, 11)
        await self.memory.save_turn("other", "private question", "private reply")
        await self.memory.save_turn("user", "new persona", "persona reply", companion_id="other")
        await self.memory.save_turn("user", "unfinished", "")

        reopened = SQLiteMemoryService(self.path)
        await reopened.initialize()
        self.assertTrue(await reopened.ping())
        recent = await reopened.recent_turn_messages("user", companion_id="default")

        self.assertEqual(len(recent), 20)
        self.assertEqual(recent[:2], [("user", "message 1"), ("assistant", "reply 1")])
        self.assertEqual(recent[-2:], [("user", "message 10"), ("assistant", "reply 10")])
        self.assertEqual(
            await reopened.recent_turn_messages("user", companion_id="other"),
            [("user", "new persona"), ("assistant", "persona reply")],
        )

    async def test_compaction_retains_recent_turns_and_recalls_promoted_summary(self):
        summaries = ["用户养了一只布偶猫布丁", "用户喝绿茶", "用户住青岛", "用户喜欢跑步", "用户上班坐地铁"]
        await self.add_turns(0, 8)
        for batch, summary in enumerate(summaries):
            await self.add_turns(8 + batch * 3, 3)
            summarize = AsyncMock(return_value=summary)
            await self.memory.run_compaction(summarize)
            self.assertTrue(summarize.call_args.args[0].startswith(f"user: message {batch * 3}\n"))

        query = "布丁是什么品种"
        messages = await self.memory.build_messages("user", "persona", query)
        self.assertEqual(messages[0], ("system", "persona"))
        self.assertEqual(messages[1], ("user", "message 15"))
        self.assertIn('"相关过往回忆": ["用户养了一只布偶猫布丁"]', messages[-1][1])
        self.assertIn(summaries[-1], messages[-1][1])
        self.assertEqual(
            await self.memory.build_messages("another", "persona", query),
            [("system", "persona"), ("user", query)],
        )

    async def test_failed_model_preserves_turns_for_retry(self):
        await self.add_turns(0, 11)
        failure = AsyncMock(side_effect=RuntimeError("model unavailable"))
        with self.assertRaises(RuntimeError):
            await self.memory.run_compaction(failure)
        await self.memory.run_compaction(AsyncMock(return_value=""))

        summary = AsyncMock(return_value="NO_INFO")
        await self.memory.run_compaction(summary)

        self.assertTrue(summary.call_args.args[0].startswith("user: message 0\n"))
        self.assertEqual(len(await self.memory.recent_turn_messages("user")), 16)

    async def test_concurrent_compaction_applies_once_and_keeps_new_turn(self):
        await self.add_turns(0, 11)
        second_store = SQLiteMemoryService(self.path)
        both_summarizing = asyncio.Event()
        release = asyncio.Event()
        arrivals = 0

        async def summarize(transcript):
            nonlocal arrivals
            arrivals += 1
            if arrivals == 2:
                both_summarizing.set()
            await release.wait()
            return "One archived batch"

        first = asyncio.create_task(self.memory.run_compaction(summarize))
        second = asyncio.create_task(second_store.run_compaction(summarize))
        try:
            await asyncio.wait_for(both_summarizing.wait(), timeout=3)
            await self.add_turns(11, 1)
        finally:
            release.set()
            await asyncio.gather(first, second)

        recent = await self.memory.recent_turn_messages("user")
        self.assertEqual(len(recent), 18)
        self.assertEqual(recent[0], ("user", "message 3"))
        self.assertEqual(recent[-1], ("assistant", "reply 11"))
