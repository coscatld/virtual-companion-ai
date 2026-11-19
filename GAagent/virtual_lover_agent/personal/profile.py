import asyncio
import os
import secrets
import sqlite3
from contextlib import closing

from pydantic import BaseModel, Field, field_validator

from virtual_lover_agent.app.dialogue import DEFAULT_PROMPT, Companion
from virtual_lover_agent.personal.config import PersonalSettings

PERSONAL_USER_ID = "personal"


class PersonalProfile(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(min_length=1, max_length=12_000)
    voice_id: str = Field(default="", max_length=120)

    @field_validator("name", "system_prompt")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain text")
        return value.strip()

    def companion(self) -> Companion:
        return Companion(PERSONAL_USER_ID, system_prompt=self.system_prompt, voice_id=self.voice_id)


class PersonalSettingsStore:
    def __init__(self, settings: PersonalSettings):
        self.path = settings.data_dir / "ga.sqlite3"
        self.default_profile = PersonalProfile(
            name=settings.personal_name,
            system_prompt=settings.personal_system_prompt or DEFAULT_PROMPT,
            voice_id=settings.personal_voice_id,
        )
        self.token_override = settings.personal_token
        if self.token_override and any(not 33 <= ord(c) <= 126 for c in self.token_override):
            raise ValueError("GA_PERSONAL_TOKEN must contain printable ASCII characters without whitespace")

    async def initialize(self) -> str:
        return await asyncio.to_thread(self._initialize)

    def _initialize(self) -> str:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS personal_profile (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                token TEXT NOT NULL,
                name TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                voice_id TEXT NOT NULL
            )""")
            get_token = "SELECT token FROM personal_profile WHERE singleton = 1"
            row = connection.execute(get_token).fetchone()
            if row is None:
                connection.execute(
                    "INSERT OR IGNORE INTO personal_profile VALUES (1, ?, ?, ?, ?)",
                    (secrets.token_urlsafe(32), self.default_profile.name, self.default_profile.system_prompt,
                     self.default_profile.voice_id),
                )
                row = connection.execute(get_token).fetchone()
            token, = row
        if os.name != "nt":
            self.path.chmod(0o600)
        return self.token_override or token

    async def read(self) -> PersonalProfile:
        return await asyncio.to_thread(self._read)

    def _read(self) -> PersonalProfile:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            row = connection.execute(
                "SELECT name, system_prompt, voice_id FROM personal_profile WHERE singleton = 1"
            ).fetchone()
        if row is None:
            raise sqlite3.DatabaseError("Personal profile is missing")
        return PersonalProfile(name=row[0], system_prompt=row[1], voice_id=row[2])

    async def update(self, profile: PersonalProfile) -> None:
        await asyncio.to_thread(self._update, profile)

    def _update(self, profile: PersonalProfile) -> None:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection, connection:
            cursor = connection.execute(
                "UPDATE personal_profile SET name = ?, system_prompt = ?, voice_id = ? WHERE singleton = 1",
                (profile.name, profile.system_prompt, profile.voice_id),
            )
            if cursor.rowcount != 1:
                raise sqlite3.DatabaseError("Personal profile is missing")
