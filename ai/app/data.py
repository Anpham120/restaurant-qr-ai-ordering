from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from app.domain import MenuItemContext, RetrievalDocument


def load_policy_documents(path: Path) -> list[RetrievalDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents: list[RetrievalDocument] = []
    for item in payload:
        aliases = [str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()]
        answer = str(item["answer"]).strip()
        documents.append(
            RetrievalDocument(
                id=f"policy:{item['id']}",
                kind="policy",
                source=path.name,
                title=str(item["title"]).strip(),
                text="\n".join([str(item["title"]).strip(), *aliases, answer]),
                answer=answer,
                metadata={"aliases": aliases},
            )
        )
    return documents


def documents_from_menu(items: Iterable[MenuItemContext]) -> list[RetrievalDocument]:
    documents: list[RetrievalDocument] = []
    for item in items:
        if not item.is_available:
            continue
        text = "\n".join(
            part
            for part in [
                item.name,
                item.category_name,
                item.description,
                " ".join(item.tags),
            ]
            if part
        )
        documents.append(
            RetrievalDocument(
                id=f"menu:{item.id}",
                kind="menu",
                source="live-menu",
                title=item.name,
                text=text,
                menu_item_id=item.id,
                metadata=item.to_mapping(),
            )
        )
    return documents


def menu_fingerprint(items: Iterable[MenuItemContext]) -> str:
    canonical = [item.to_mapping() for item in sorted(items, key=lambda value: value.id)]
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

