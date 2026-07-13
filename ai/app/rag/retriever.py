from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from app.rag.knowledge_base import KnowledgeChunk


TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

# Okapi BM25 hyper-parameters (standard defaults from Robertson et al.)
BM25_K1 = 1.5
BM25_B = 0.75

# Bonus weights for matches in title or tags (improves precision)
TITLE_BOOST = 1.5
TAG_BOOST = 1.0


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    score: float


@dataclass(frozen=True)
class RetrievalFilters:
    """Hard metadata constraints applied before a retriever ranks candidates."""

    allowed_source_ids: frozenset[str] | None = None
    excluded_source_ids: frozenset[str] = frozenset()
    required_tags: frozenset[str] = frozenset()

    def allows(self, chunk: KnowledgeChunk) -> bool:
        if self.allowed_source_ids is not None and chunk.source not in self.allowed_source_ids:
            return False
        if chunk.source in self.excluded_source_ids:
            return False
        return self.required_tags.issubset(chunk.tags)


class Retriever(Protocol):
    """Common contract for lexical, dense, and hybrid retrieval."""

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]: ...


class BM25Retriever:
    """Okapi BM25 retriever with title/tag boosting.

    BM25 improves over raw TF-IDF by normalising term frequency with
    document length and controlling saturation via *k1* and *b*.

    Score(q, D) = Σ IDF(t) · ( tf(t,D) · (k1+1) ) / ( tf(t,D) + k1 · (1 - b + b · |D|/avgdl) )

    On top of standard BM25 we add additive boosts when query tokens
    appear in the chunk *title* or *tags* to nudge the ranking towards
    the most topically relevant chunks.
    """

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks

        # Pre-tokenise each chunk's full text (title + content + tags)
        self._chunk_tokens: list[list[str]] = []
        self._chunk_token_sets: list[set[str]] = []
        for chunk in chunks:
            tokens = _tokenize_list(chunk.title + " " + chunk.content + " " + " ".join(chunk.tags))
            self._chunk_tokens.append(tokens)
            self._chunk_token_sets.append(set(tokens))

        # Pre-compute corpus-level statistics
        self._num_docs = len(chunks)
        total_tokens = sum(len(tokens) for tokens in self._chunk_tokens)
        self._avg_doc_len = total_tokens / max(self._num_docs, 1)

        # Document frequency for each token (how many docs contain it)
        self._doc_freq: dict[str, int] = {}
        for token_set in self._chunk_token_sets:
            for token in token_set:
                self._doc_freq[token] = self._doc_freq.get(token, 0) + 1

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            return []

        query_tokens = _tokenize_set(query)
        if not query_tokens:
            return []

        scored: list[RetrievedChunk] = []

        for idx, chunk in enumerate(self._chunks):
            if filters is not None and not filters.allows(chunk):
                continue

            doc_tokens = self._chunk_tokens[idx]
            doc_token_set = self._chunk_token_sets[idx]

            # Quick check: any overlap at all?
            overlap = query_tokens.intersection(doc_token_set)
            if not overlap:
                continue

            doc_len = len(doc_tokens)

            # Term frequency map for this document
            tf_map: dict[str, int] = {}
            for token in doc_tokens:
                tf_map[token] = tf_map.get(token, 0) + 1

            # BM25 score
            score = 0.0
            for token in overlap:
                tf = tf_map.get(token, 0)
                df = self._doc_freq.get(token, 0)
                idf = math.log((self._num_docs - df + 0.5) / (df + 0.5) + 1.0)
                numerator = tf * (BM25_K1 + 1)
                denominator = tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / self._avg_doc_len)
                score += idf * numerator / denominator

            # Title boost: extra score for query tokens found in title
            title_tokens = _tokenize_set(chunk.title)
            score += TITLE_BOOST * len(query_tokens.intersection(title_tokens))

            # Tag boost: extra score for query tokens found in tags
            tag_tokens = set(chunk.tags)
            score += TAG_BOOST * len(query_tokens.intersection(tag_tokens))

            scored.append(RetrievedChunk(chunk=chunk, score=round(score, 4)))

        return sorted(scored, key=lambda item: (-item.score, item.chunk.source))[:top_k]


# Keep the old class name as an alias for backward compatibility
LexicalRetriever = BM25Retriever


def _tokenize_list(text: str) -> list[str]:
    """Tokenise *text* into a list of lowercase ASCII tokens (preserving duplicates for TF)."""
    normalized = unicodedata.normalize("NFKD", text.lower()).replace("đ", "d")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return TOKEN_PATTERN.findall(ascii_text)


def _tokenize_set(text: str) -> set[str]:
    """Tokenise *text* into a unique set of lowercase ASCII tokens."""
    return set(_tokenize_list(text))
