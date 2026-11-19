import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from dotenv import load_dotenv

if TYPE_CHECKING:
    from virtual_lover_agent.enterprise.config import EnterpriseSettings
    from virtual_lover_agent.personal.config import PersonalSettings


@dataclass(frozen=True)
class ProviderSettings:
    kind: str
    base_url: str
    model: str
    api_key: str = field(repr=False)


@dataclass(frozen=True)
class InferenceSettings:
    llm: ProviderSettings
    summary: ProviderSettings
    public_tools: bool
    asr: ProviderSettings
    tts: ProviderSettings
    tts_voice: str


def load_environment() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def read_provider(prefix: str, *, kind: str = "disabled") -> ProviderSettings:
    return ProviderSettings(
        os.getenv(f"{prefix}_PROVIDER") or kind,
        os.getenv(f"{prefix}_BASE_URL", "").strip(),
        os.getenv(f"{prefix}_MODEL", "").strip(),
        os.getenv(f"{prefix}_API_KEY", ""),
    )


def summary_provider(prefix: str, llm: ProviderSettings) -> ProviderSettings:
    url = os.getenv(f"{prefix}_BASE_URL", "").strip() or llm.base_url
    same_endpoint = url.rstrip("/") == llm.base_url.rstrip("/")
    return ProviderSettings(
        "openai", url, os.getenv(f"{prefix}_MODEL", "").strip() or llm.model,
        os.getenv(f"{prefix}_API_KEY") or (llm.api_key if same_endpoint else ""),
    )


def validate_api_url(url: str, setting: str) -> None:
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname and parsed.username is None
        if valid:
            _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{setting} must be an absolute HTTP(S) API base URL without credentials")


def http_origins() -> tuple[str, ...]:
    return tuple(origin.strip() for origin in os.getenv("GA_HTTP_ALLOWED_ORIGINS", "").split(",") if origin.strip())


class Settings:
    """Compatibility factory used by the combined entry points."""

    @classmethod
    def from_env(cls, *, default_mode: str = "enterprise", mode: str | None = None) -> "EnterpriseSettings | PersonalSettings":
        load_environment()
        selected = mode or os.getenv("GA_MODE") or default_mode
        if selected == "personal":
            from virtual_lover_agent.personal.config import PersonalSettings

            return PersonalSettings.from_env()
        if selected == "enterprise":
            from virtual_lover_agent.enterprise.config import EnterpriseSettings

            return EnterpriseSettings.from_env()
        raise ValueError("GA_MODE must be personal or enterprise")
