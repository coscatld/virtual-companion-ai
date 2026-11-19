import os
from dataclasses import dataclass, field

from virtual_lover_agent.app.config import (
    InferenceSettings, ProviderSettings, load_environment, read_provider, summary_provider, validate_api_url,
)


def read_enterprise_model() -> ProviderSettings:
    llm = read_provider("GA_ENTERPRISE_LLM", kind="openai")
    if llm.kind not in {"openai", "mock"}:
        raise ValueError("GA_ENTERPRISE_LLM_PROVIDER must be openai or mock")
    if llm.kind == "mock":
        return llm
    if not (llm.base_url or llm.model or llm.api_key):
        llm = ProviderSettings(
            llm.kind, os.getenv("deepseek_url", "").strip(), os.getenv("deepseek_model", "").strip(),
            os.getenv("deepseek_api_key", ""),
        )
    if not llm.base_url or not llm.model:
        raise ValueError("GA_ENTERPRISE_LLM_BASE_URL and GA_ENTERPRISE_LLM_MODEL are required for enterprise mode")
    validate_api_url(llm.base_url, "GA_ENTERPRISE_LLM_BASE_URL")
    return llm


@dataclass(frozen=True)
class EnterpriseSettings(InferenceSettings):
    redis_url: str = field(repr=False)
    gateway_url: str
    internal_token: str = field(repr=False)
    grpc_bind: str
    mode = "enterprise"

    @classmethod
    def from_env(cls) -> "EnterpriseSettings":
        load_environment()
        llm = read_enterprise_model()
        summary = summary_provider("GA_ENTERPRISE_SUMMARY", llm)
        if llm.kind != "mock":
            validate_api_url(summary.base_url, "GA_ENTERPRISE_SUMMARY_BASE_URL")
        redis_host = os.getenv("redis_host", "127.0.0.1")
        redis_port = os.getenv("redis_port", "6379")
        return cls(
            llm=llm,
            summary=summary,
            public_tools=os.getenv("GA_ENTERPRISE_ENABLE_PUBLIC_TOOLS", "false").lower() == "true",
            asr=read_provider("GA_ENTERPRISE_ASR"),
            tts=read_provider("GA_ENTERPRISE_TTS"),
            tts_voice=os.getenv("GA_ENTERPRISE_TTS_VOICE", ""),
            redis_url=os.getenv("GA_REDIS_URL") or f"redis://{redis_host}:{redis_port}/0",
            gateway_url=os.getenv("GA_GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/"),
            internal_token=os.getenv("GA_INTERNAL_TOKEN", ""),
            grpc_bind=os.getenv("GA_GRPC_BIND", "127.0.0.1:7000"),
        )
