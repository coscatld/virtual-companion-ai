import os
from dataclasses import dataclass, field
from pathlib import Path

from virtual_lover_agent.app.config import (
    InferenceSettings, ProviderSettings, http_origins, load_environment, read_provider, summary_provider,
)


def default_data_dir() -> Path:
    if os.name == "nt":
        return Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "GA"
    return Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "ga"


@dataclass(frozen=True)
class PersonalSettings(InferenceSettings):
    data_dir: Path
    personal_token: str = field(repr=False)
    personal_name: str
    personal_system_prompt: str
    personal_voice_id: str
    http_host: str
    http_port: int
    http_origins: tuple[str, ...]
    mode = "personal"

    @classmethod
    def from_env(cls) -> "PersonalSettings":
        load_environment()
        provider = read_provider("GA_LLM", kind="openai")
        llm = ProviderSettings(
            provider.kind, provider.base_url or "http://127.0.0.1:8000/v1",
            provider.model or "Qwen/Qwen2.5-7B-Instruct", provider.api_key,
        )
        return cls(
            llm=llm,
            summary=summary_provider("GA_SUMMARY", llm),
            public_tools=os.getenv("GA_ENABLE_PUBLIC_TOOLS", "false").lower() == "true",
            asr=read_provider("GA_ASR"),
            tts=read_provider("GA_TTS"),
            tts_voice=os.getenv("GA_TTS_VOICE", ""),
            data_dir=Path(os.getenv("GA_DATA_DIR") or default_data_dir()).expanduser(),
            personal_token=os.getenv("GA_PERSONAL_TOKEN", ""),
            personal_name=os.getenv("GA_PERSONAL_NAME", "GA 伴侣"),
            personal_system_prompt=os.getenv("GA_PERSONAL_SYSTEM_PROMPT", ""),
            personal_voice_id=os.getenv("GA_PERSONAL_VOICE_ID", ""),
            http_host=os.getenv("GA_HTTP_HOST", "127.0.0.1"),
            http_port=int(os.getenv("GA_HTTP_PORT", "8081")),
            http_origins=http_origins(),
        )
