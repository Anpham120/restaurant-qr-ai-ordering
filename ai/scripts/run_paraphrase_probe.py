# -*- coding: utf-8 -*-
"""Paraphrase routing probes for intent keyword router regression."""
from __future__ import annotations

PROBES: list[dict[str, object]] = [
    {
        "id": "recommend-party-4",
        "message": "gợi ý món cho 4 người",
        "history": [],
        "wants": True,
        "party": 4,
    },
    {
        "id": "browse-no-party",
        "message": "xem menu món chính",
        "history": [],
        "wants": False,
        "party": None,
    },
]
