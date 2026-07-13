from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
            self.provider.lower() == "9router"
            and bool(self.base_url.strip())
            and bool(self.api_key.strip())
            and bool(self.model.strip())
        )


def load_config() -> AiServiceConfig:
    return AiServiceConfig(
        provider=os.getenv("AI_PROVIDER", "9router"),
        base_url=os.getenv("AI_BASE_URL", "http://127.0.0.1:20128/v1"),
        api_key=os.getenv("AI_API_KEY", ""),
        model=os.getenv("AI_MODEL", "gh/gpt-4o"),
        timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "30")),
        knowledge_base_path=Path(os.getenv("RAG_KNOWLEDGE_BASE_PATH", "knowledge-base")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
    )
