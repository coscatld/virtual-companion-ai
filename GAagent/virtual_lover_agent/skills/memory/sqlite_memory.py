import asyncio
import logging
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from virtual_lover_agent.skills.memory.context import (
    COMPACTION_TURNS,
    RECENT_TURNS,
    ROLLING_SUMMARIES,
    Message,
    Summarize,
    build_memory_context,
    history_budget,
    transcript_for,
)


logger = logging.getLogger(__name__)

Scope = tuple[str, str]
Turn = tuple[int, str, str]

SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS ga_dialogue_turns (
    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    companion_id TEXT NOT NULL,
    user_text TEXT NOT NULL,
    assistant_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ga_dialogue_turn_scope
    ON ga_dialogue_turns (user_id, companion_id, turn_id);
CREATE TABLE IF NOT EXISTS ga_dialogue_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    companion_id TEXT NOT NULL,
    content TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
);
CREATE INDEX IF NOT EXISTS ga_dialogue_summary_scope
    ON ga_dialogue_summaries (user_id, companion_id, archived, summary_id);
COMMIT;
"""


def _turn_messages(turns: Iterable[Turn]) -> list[Message]:
    return [
        message
        for _, user_text, assistant_text in turns
        for message in (("user", user_text), ("assistant", assistant_text))
    ]


def _oldest_turns(db: sqlite3.Connection, scope: Scope) -> list[Turn]:
    return db.execute(
        """
        SELECT turn_id, user_text, assistant_text FROM ga_dialogue_turns
        WHERE user_id = ? AND companion_id = ?
        ORDER BY turn_id LIMIT ?
        """,
        (*scope, COMPACTION_TURNS),
    ).fetchall()


def _newest_turns(db: sqlite3.Connection, scope: Scope) -> list[Turn]:
    newest = db.execute(
        """
        SELECT turn_id, user_text, assistant_text FROM ga_dialogue_turns
        WHERE user_id = ? AND companion_id = ?
        ORDER BY turn_id DESC LIMIT ?
        """,
        (*scope, RECENT_TURNS),
    ).fetchall()
    return newest[::-1]


class SQLiteMemoryService:
    """Local dialogue memory stored alongside the personal node's profile data."""

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            yield db

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize)

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(SCHEMA)

    async def ping(self) -> bool:
        return await asyncio.to_thread(self._ping)

    def _ping(self) -> bool:
        with self._connect() as db:
            db.execute("SELECT turn_id FROM ga_dialogue_turns LIMIT 1").fetchone()
        return True

    async def recent_turn_messages(
        self, user_id: str, *, companion_id: str = ""
    ) -> list[Message]:
        return await asyncio.to_thread(self._read_turns, (user_id, companion_id or "default"))

    def _read_turns(self, scope: Scope) -> list[Message]:
        with self._connect() as db:
            return _turn_messages(_newest_turns(db, scope))

    async def build_messages(
        self, user_id: str, system_prompt: str, user_text: str, *, companion_id: str = ""
    ) -> list[Message]:
        if history_budget(system_prompt, user_text) <= 0:
            return [("system", system_prompt), ("user", user_text)]

        scope = (user_id, companion_id or "default")
        try:
            return await asyncio.to_thread(self._build_messages, scope, system_prompt, user_text)
        except sqlite3.Error:
            logger.warning("SQLite dialogue memory unavailable while building model context")
            return [("system", system_prompt), ("user", user_text)]

    def _build_messages(self, scope: Scope, system_prompt: str, user_text: str) -> list[Message]:
        with self._connect() as db:
            db.execute("BEGIN")
            history = _turn_messages(_newest_turns(db, scope))
            rows = db.execute(
                """
                SELECT content, archived FROM ga_dialogue_summaries
                WHERE user_id = ? AND companion_id = ? ORDER BY summary_id
                """,
                scope,
            ).fetchall()
        summaries, archive = [], []
        for content, archived in rows:
            (archive if archived else summaries).append(content)
        return build_memory_context(system_prompt, user_text, history, summaries, archive)

    async def save_turn(
        self, user_id: str, user_text: str, assistant_text: str, *, companion_id: str = ""
    ) -> None:
        if not user_id or not user_text.strip() or not assistant_text.strip():
            return
        await asyncio.to_thread(
            self._save_turn, (user_id, companion_id or "default"), user_text, assistant_text,
        )

    def _save_turn(self, scope: Scope, user_text: str, assistant_text: str) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO ga_dialogue_turns (user_id, companion_id, user_text, assistant_text)
                VALUES (?, ?, ?, ?)
                """,
                (*scope, user_text, assistant_text),
            )

    async def run_compaction(self, summarize: Summarize) -> None:
        try:
            for scope in await asyncio.to_thread(self._overflowing_scopes):
                await self._compact(scope, summarize)
        except sqlite3.Error as error:
            logger.warning("SQLite unavailable to memory worker (%s)", type(error).__name__)

    def _overflowing_scopes(self) -> list[Scope]:
        with self._connect() as db:
            return db.execute(
                """
                SELECT user_id, companion_id FROM ga_dialogue_turns
                GROUP BY user_id, companion_id HAVING count(*) > ?
                """,
                (RECENT_TURNS,),
            ).fetchall()

    async def _compact(self, scope: Scope, summarize: Summarize) -> bool:
        oldest = await asyncio.to_thread(self._compaction_snapshot, scope)
        if not oldest:
            return False

        summary = (await summarize(transcript_for(_turn_messages(oldest)))).strip()
        if not summary:
            return False
        return await asyncio.to_thread(self._commit_compaction, scope, oldest, summary)

    def _compaction_snapshot(self, scope: Scope) -> list[Turn]:
        with self._connect() as db:
            db.execute("BEGIN")
            has_overflow = db.execute(
                """
                SELECT 1 FROM ga_dialogue_turns WHERE user_id = ? AND companion_id = ?
                ORDER BY turn_id LIMIT 1 OFFSET ?
                """,
                (*scope, RECENT_TURNS),
            ).fetchone()
            return _oldest_turns(db, scope) if has_overflow else []

    def _commit_compaction(self, scope: Scope, oldest: list[Turn], summary: str) -> bool:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if _oldest_turns(db, scope) != oldest:
                return False

            if summary.upper() != "NO_INFO":
                db.execute(
                    "INSERT INTO ga_dialogue_summaries (user_id, companion_id, content) VALUES (?, ?, ?)",
                    (*scope, summary),
                )
                db.execute(
                    """
                    UPDATE ga_dialogue_summaries SET archived = 1 WHERE summary_id IN (
                        SELECT summary_id FROM ga_dialogue_summaries
                        WHERE user_id = ? AND companion_id = ? AND archived = 0
                        ORDER BY summary_id DESC LIMIT -1 OFFSET ?
                    )
                    """,
                    (*scope, ROLLING_SUMMARIES),
                )
            db.execute(
                "DELETE FROM ga_dialogue_turns WHERE user_id = ? AND companion_id = ? AND turn_id <= ?",
                (*scope, oldest[-1][0]),
            )
        return True
