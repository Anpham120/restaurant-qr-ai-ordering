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
    timeout_seconds: float
    knowledge_base_path: Path
    top_k: int

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
        model=os.getenv("AI_MODEL", "gemini-2.5-flash"),
        timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "30")),
        knowledge_base_path=Path(os.getenv("RAG_KNOWLEDGE_BASE_PATH", "knowledge-base")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
    )
