from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


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

    @property
    def timeout_seconds(self) -> float:
        """Backward-compatible alias for LLM timeout."""

        return self.llm_timeout_seconds

    @property
    def llm_enabled(self) -> bool:
        return (
            self.provider.lower() == "gemini"
            and bool(self.base_url.strip())
            and bool(self.api_key.strip())
            and bool(self.model.strip())
        )


def load_config() -> AiServiceConfig:
    return AiServiceConfig(
        provider=os.getenv("AI_PROVIDER", "gemini"),
        base_url=GEMINI_OPENAI_BASE_URL,
        api_key=os.getenv("GEMINI_API_KEY", ""),
        model=os.getenv("AI_MODEL", "gemini-3.5-flash"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", os.getenv("AI_TIMEOUT_SECONDS", "8"))),
        request_budget_seconds=float(os.getenv("AI_REQUEST_BUDGET_SECONDS", "10")),
        max_retry=int(os.getenv("AI_MAX_RETRY", "0")),
        max_tokens=int(os.getenv("AI_MAX_TOKENS", "700")),
        reasoning_effort=os.getenv("AI_REASONING_EFFORT", "low"),
        knowledge_base_path=Path(os.getenv("RAG_KNOWLEDGE_BASE_PATH", "knowledge-base")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
        retrieval_method=os.getenv("RAG_RETRIEVAL_METHOD", "hybrid"),
    )
