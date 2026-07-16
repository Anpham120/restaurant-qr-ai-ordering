from __future__ import annotations

from typing import Protocol

from app.domain import SearchResult


class Retriever(Protocol):
    name: str

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]: ...

