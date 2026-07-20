from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_API_HOST = "generativelanguage.googleapis.com"
DEFAULT_ROUTER_BASE_URL = "http://localhost:20128/v1"
LLM_PROVIDERS = frozenset({"gemini", "openai", "router"})


def is_gemini_api_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url.strip())
    return parsed.hostname == GEMINI_API_HOST


@dataclass(frozen=True)
class AiServiceConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    llm_timeout_seconds: float
    request_budget_seconds: float
    max_retry: int
    max_tokens: int
    reasoning_effort: str
    knowledge_base_path: Path
    top_k: int
    retrieval_method: str = "hybrid"
    embedding_model: str = "e5_small"
    llm_intent_classification_enabled: bool = True
    intent_classification_timeout_seconds: float = 2.5

    @property
    def timeout_seconds(self) -> float:
        """Backward-compatible alias for LLM timeout."""

        return self.llm_timeout_seconds

    @property
    def llm_enabled(self) -> bool:
        return (
            self.provider.lower() in LLM_PROVIDERS
            and bool(self.base_url.strip())
            and bool(self.api_key.strip())
            and bool(self.model.strip())
        )

    @property
    def uses_gemini_native_features(self) -> bool:
        return is_gemini_api_base_url(self.base_url)


def _resolve_api_key(provider: str) -> str:
    custom_base = os.getenv("AI_BASE_URL", "").strip()
    if provider.lower() == "gemini" and not custom_base:
        return os.getenv("GEMINI_API_KEY", "").strip()

    for name in ("AI_API_KEY", "OPENAI_API_KEY", "ROUTER_API_KEY", "GEMINI_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _resolve_base_url(provider: str) -> str:
    custom = os.getenv("AI_BASE_URL", "").strip().rstrip("/")
    if custom:
        return custom
    if provider.lower() == "gemini":
        return GEMINI_OPENAI_BASE_URL
    return os.getenv("OPENAI_BASE_URL", DEFAULT_ROUTER_BASE_URL).strip().rstrip("/")


def load_config() -> AiServiceConfig:
    _load_env_file()
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    return AiServiceConfig(
        provider=provider,
        base_url=_resolve_base_url(provider),
        api_key=_resolve_api_key(provider),
        model=os.getenv("AI_MODEL", "gemini-3.5-flash"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", os.getenv("AI_TIMEOUT_SECONDS", "12"))),
        request_budget_seconds=float(os.getenv("AI_REQUEST_BUDGET_SECONDS", "22")),
        max_retry=int(os.getenv("AI_MAX_RETRY", "0")),
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "700")),
        reasoning_effort=os.getenv("AI_REASONING_EFFORT", "low"),
        knowledge_base_path=Path(os.getenv("RAG_KNOWLEDGE_BASE_PATH", "knowledge-base")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
        retrieval_method=os.getenv("RAG_RETRIEVAL_METHOD", "hybrid"),
        embedding_model=os.getenv("AI_EMBEDDING_MODEL", "e5_small"),
        llm_intent_classification_enabled=os.getenv(
            "AI_LLM_INTENT_CLASSIFICATION_ENABLED", "true"
        ).strip().lower()
        in {"1", "true", "yes", "on"},
        intent_classification_timeout_seconds=float(
            os.getenv("AI_INTENT_CLASSIFICATION_TIMEOUT_SECONDS", "2.5")
        ),
    )


def _load_env_file() -> None:
    """Load ai/.env for local dev; existing shell env vars win."""

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
