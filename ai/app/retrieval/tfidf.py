from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.domain import RetrievalDocument, SearchResult
from app.text import normalize_text


class TfidfRetriever:
    name = "tfidf"

    def __init__(self, documents: list[RetrievalDocument]) -> None:
        self.documents = documents
        self._vectorizer = TfidfVectorizer(
            preprocessor=normalize_text,
            tokenizer=str.split,
            token_pattern=None,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(document.text for document in documents)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not query.strip() or not self.documents:
            return []
        query_vector = self._vectorizer.transform([query])
        scores = (self._matrix @ query_vector.T).toarray().ravel()
        indices = np.argsort(-scores)[:top_k]
        return [
            SearchResult(document=self.documents[int(index)], score=float(scores[index]), rank=rank)
            for rank, index in enumerate(indices, start=1)
            if scores[index] > 0
        ]

