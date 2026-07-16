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
    max_output_tokens: int
    policies_path: Path
    production_config_path: Path
    embedding_cache_path: Path
    embedding_model_path: Path | None
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
        model=os.getenv("AI_MODEL", "gc/gemini-3-flash"),
        timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "7")),
        max_output_tokens=int(os.getenv("AI_MAX_OUTPUT_TOKENS", "220")),
        policies_path=Path(os.getenv("AI_POLICIES_PATH", "data/policies.json")),
        production_config_path=Path(
            os.getenv("RAG_PRODUCTION_CONFIG_PATH", "research/artifacts/production_config.json")
        ),
        embedding_cache_path=Path(os.getenv("EMBEDDING_CACHE_PATH", ".cache/fastembed")),
        embedding_model_path=(
            Path(os.environ["EMBEDDING_MODEL_PATH"]) if os.getenv("EMBEDDING_MODEL_PATH") else None
        ),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
    )
