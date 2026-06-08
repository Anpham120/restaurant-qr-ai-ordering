from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

from app.rag.knowledge_base import KnowledgeChunk


TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    score: float


class LexicalRetriever:
    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks
        self._chunk_tokens = [_tokenize(chunk.title + " " + chunk.content + " " + " ".join(chunk.tags)) for chunk in chunks]

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[RetrievedChunk] = []
        for chunk, tokens in zip(self._chunks, self._chunk_tokens):
            overlap = query_tokens.intersection(tokens)
            if not overlap:
                continue

            score = sum(_idf_like(token, self._chunk_tokens) for token in overlap)
            title_tokens = _tokenize(chunk.title)
            tag_tokens = set(chunk.tags)
            score += 0.75 * len(query_tokens.intersection(title_tokens))
            score += 0.5 * len(query_tokens.intersection(tag_tokens))
            score = score / math.sqrt(max(len(tokens), 1))
            scored.append(RetrievedChunk(chunk=chunk, score=round(score, 4)))

        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


def _tokenize(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower()).replace("đ", "d")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return set(TOKEN_PATTERN.findall(ascii_text))


def _idf_like(token: str, corpus_tokens: list[set[str]]) -> float:
    doc_count = sum(1 for tokens in corpus_tokens if token in tokens)
    return 1.0 + math.log((len(corpus_tokens) + 1) / (doc_count + 1))
