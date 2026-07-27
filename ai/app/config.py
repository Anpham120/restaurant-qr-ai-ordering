from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_ROUTER_BASE_URL = "http://localhost:20128/v1"
DEFAULT_LLM_MODEL = "oc/deepseek-v4-flash-free"
DEFAULT_RATE_LIMIT_FALLBACK_MODEL = "cx/gpt-5.6-luna-review"
DEFAULT_PIPELINE_PROFILE = "llm_first_v1"
PIPELINE_PROFILES = frozenset(
    {
        "llm_first_v1",
        "evidence_first_v2",
        "planner_state_v3",
    }
)
LLM_PROVIDERS = frozenset({"9router"})
LEGACY_ROUTER_PROVIDER_NAMES = frozenset({"router", "openai"})
DISALLOWED_LLM_HOST = "generativelanguage.googleapis.com"


def is_supported_router_model(model: str) -> bool:
    normalized = model.strip().casefold()
    return (
        "gpt-5.5" in normalized
        or "deepseek" in normalized
        or normalized == DEFAULT_RATE_LIMIT_FALLBACK_MODEL
    )


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
    internal_token: str = ""
    pipeline_version: str = "v2"
    rag_config_id: str = "default"
    llm_first: bool = True
    pipeline_profile: str = DEFAULT_PIPELINE_PROFILE
    rate_limit_fallback_model: str | None = None
    rate_limit_fallback_enabled: bool = False

    @property
    def timeout_seconds(self) -> float:
        """Backward-compatible alias for LLM timeout."""

        return self.llm_timeout_seconds

    @property
    def llm_enabled(self) -> bool:
        return (
            self.provider.casefold() in LLM_PROVIDERS
            and bool(self.base_url.strip())
            and bool(self.api_key.strip())
            and is_supported_router_model(self.model)
        )

    @property
    def model_policy_valid(self) -> bool:
        if not self.rate_limit_fallback_enabled:
            return True
        return (
            self.model == DEFAULT_LLM_MODEL
            and self.rate_limit_fallback_model == DEFAULT_RATE_LIMIT_FALLBACK_MODEL
            and self.model != self.rate_limit_fallback_model
        )


def _resolve_api_key() -> str:
    value = _canonical_env(
        "LLM_API_KEY",
        "AI_API_KEY",
        "OPENAI_API_KEY",
        "ROUTER_API_KEY",
    )
    if value:
        return value.strip()
    return ""


def _resolve_base_url() -> str:
    custom = _canonical_env("LLM_BASE_URL", "AI_BASE_URL").strip().rstrip("/")
    if custom:
        return custom
    return _env("OPENAI_BASE_URL", default=DEFAULT_ROUTER_BASE_URL).strip().rstrip("/")


def _resolve_provider() -> str:
    raw = _canonical_env("LLM_PROVIDER", "AI_PROVIDER", default="9router").strip().casefold()
    if raw in LEGACY_ROUTER_PROVIDER_NAMES:
        warnings.warn(
            f"LLM provider value '{raw}' is deprecated; use '9router'",
            DeprecationWarning,
            stacklevel=3,
        )
        return "9router"
    if raw != "9router":
        raise ValueError("Only the 9router provider is supported; Gemini has been removed")
    return raw


def _is_disallowed_gemini_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url.strip())
    host = parsed.hostname
    if not host:
        return False
    normalized = host.casefold().rstrip(".")
    blocked = DISALLOWED_LLM_HOST.casefold()
    return normalized == blocked or normalized.endswith(f".{blocked}")


def load_config() -> AiServiceConfig:
    _load_env_file()
    provider = _resolve_provider()
    base_url = _resolve_base_url()
    model = _canonical_env("LLM_MODEL", "AI_MODEL", default=DEFAULT_LLM_MODEL).strip()
    if _is_disallowed_gemini_base_url(base_url):
        raise ValueError("Gemini endpoints are not supported; configure the 9router base URL")
    if not is_supported_router_model(model):
        raise ValueError("LLM_MODEL must select GPT-5.5 or DeepSeek through 9router")
    rate_limit_fallback_enabled = _env_flag(
        "LLM_RATE_LIMIT_FALLBACK_ENABLED",
        default=False,
    )
    configured_fallback_model = os.getenv(
        "LLM_RATE_LIMIT_FALLBACK_MODEL",
        "",
    ).strip()
    rate_limit_fallback_model = configured_fallback_model or (
        DEFAULT_RATE_LIMIT_FALLBACK_MODEL
        if rate_limit_fallback_enabled
        else None
    )
    if rate_limit_fallback_enabled and (
        model != DEFAULT_LLM_MODEL
        or rate_limit_fallback_model != DEFAULT_RATE_LIMIT_FALLBACK_MODEL
        or model == rate_limit_fallback_model
    ):
        raise ValueError(
            "Enabled 429 failover requires DeepSeek primary and GPT-5.6 Luna fallback"
        )
    pipeline_profile = os.getenv(
        "AI_PIPELINE_PROFILE",
        DEFAULT_PIPELINE_PROFILE,
    ).strip() or DEFAULT_PIPELINE_PROFILE
    if pipeline_profile not in PIPELINE_PROFILES:
        raise ValueError(
            "AI_PIPELINE_PROFILE must be one of: "
            + ", ".join(sorted(PIPELINE_PROFILES))
        )
    return AiServiceConfig(
        provider=provider,
        base_url=base_url,
        api_key=_resolve_api_key(),
        model=model,
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
        internal_token=os.getenv("AI_INTERNAL_TOKEN", "").strip(),
        pipeline_version=os.getenv("AI_PIPELINE", "v2").strip() or "v2",
        rag_config_id=os.getenv("RAG_CONFIG_ID", "default").strip() or "default",
        llm_first=_env_flag("AI_LLM_FIRST", default=True),
        pipeline_profile=pipeline_profile,
        rate_limit_fallback_model=rate_limit_fallback_model,
        rate_limit_fallback_enabled=rate_limit_fallback_enabled,
    )


def _env_flag(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value
    return default


def _canonical_env(canonical: str, *aliases: str, default: str = "") -> str:
    """Read a canonical setting and warn when a one-release alias is used."""

    canonical_value = os.getenv(canonical)
    if canonical_value is not None and canonical_value.strip():
        return canonical_value

    for alias in aliases:
        value = os.getenv(alias)
        if value is None or not value.strip():
            continue
        warnings.warn(
            f"{alias} is deprecated and will be removed after one release; use {canonical}",
            DeprecationWarning,
            stacklevel=3,
        )
        return value
    return default


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
