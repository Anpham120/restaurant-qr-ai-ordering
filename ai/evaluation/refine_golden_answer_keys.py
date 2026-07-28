# -*- coding: utf-8 -*-
"""Refine golden answer keys from family level to per-case level.

Problem this fixes
------------------
Every one of the 25 golden families shares a single ``expected_chunk_ids`` list
across all of its cases.  Two questions in the same family therefore get graded
against the same answer key even when they ask about different things: a case
asking about the loyalty programme is scored against Happy-Hour chunks simply
because both live in the ``promotion`` family.  ``chunk_hit_rate`` then measures
the gap between the key and reality rather than whether the system retrieved the
right evidence.

Approach
--------
The key is **widened, never replaced**.  For each case we add the chunks that the
knowledge base's own author-written metadata says answer that question:

* ``<!-- question_variants: ... -->`` comments, written by whoever authored the
  KB document, list the phrasings a section is meant to answer.  A variant that
  appears verbatim inside the (normalised) question is a strong, human-authored
  signal.
* A section title whose every significant token appears in the question is the
  second accepted signal.

Both signals are independent of the retrieval system under test, so this does not
turn the evaluation into the system grading itself.  Because the metric is
``any(chunk in retrieved for chunk in expected)``, adding genuinely-relevant
chunks makes the key *more correct* — it stops punishing a correct answer that
cited a different valid section.  Nothing the original author specified is
removed.

Usage
-----
    python evaluation/refine_golden_answer_keys.py            # ghi ra file mới
    python evaluation/refine_golden_answer_keys.py --dry-run  # chỉ xem thay đổi
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from app.rag.knowledge_base import load_markdown_knowledge_base
from app.rag.vietnamese_normalizer import normalize_query_text

AI_ROOT = Path(__file__).resolve().parents[1]
GOLDEN = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"
AUDIT = AI_ROOT / "evaluation" / "results" / "golden_answer_key_refinement.json"

# Từ chức năng, không mang thông tin phân biệt chủ đề.
STOPWORDS = frozenset(
    {
        "la", "gi", "co", "khong", "nao", "the", "nhu", "toi", "minh", "ban",
        "nha", "hang", "duoc", "hay", "cho", "va", "cua", "voi", "tai", "con",
        "mon", "an", "muon", "can", "giup", "a", "o",
    }
)

# Variant ngắn hơn ngưỡng này dễ khớp bừa (ví dụ "wifi" trong "wifi pass").
MIN_VARIANT_LEN = 4


def significant_tokens(text: str) -> set[str]:
    return {
        token
        for token in normalize_query_text(text).split()
        if token not in STOPWORDS and len(token) > 2
    }


def author_written_variants(chunk) -> list[str]:
    """Các cách hỏi mà người soạn KB tự ghi cho đoạn này."""
    match = re.search(r"<!--\s*question_variants:\s*(.*?)-->", chunk.content, re.DOTALL)
    if not match:
        return []
    out: list[str] = []
    for raw in match.group(1).split(","):
        normalised = normalize_query_text(raw).strip()
        if len(normalised) >= MIN_VARIANT_LEN:
            out.append(normalised)
    return out


def chunk_key(chunk) -> str:
    """Định danh đoạn theo đúng dạng mà bộ chấm điểm so khớp."""
    return f"{chunk.source}::{chunk.title}"


def matching_chunks(query: str, kb_meta: list[tuple]) -> tuple[set[str], dict[str, str]]:
    """Trả về các đoạn khớp câu hỏi, kèm lý do khớp để phục vụ kiểm toán."""
    query_normalised = normalize_query_text(query)
    query_tokens = significant_tokens(query)

    matched: set[str] = set()
    reasons: dict[str, str] = {}
    for chunk, variants, title_tokens in kb_meta:
        key = chunk_key(chunk)
        hit_variant = next((v for v in variants if v in query_normalised), None)
        if hit_variant:
            matched.add(key)
            reasons[key] = f"question_variants: '{hit_variant}'"
            continue
        if title_tokens and title_tokens <= query_tokens:
            matched.add(key)
            reasons[key] = f"tiêu đề khớp toàn phần: {sorted(title_tokens)}"
    return matched, reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in thống kê thay đổi, không ghi file.",
    )
    parser.add_argument(
        "--kb",
        type=Path,
        default=AI_ROOT / "knowledge-base",
        help="Đường dẫn kho tri thức.",
    )
    args = parser.parse_args()

    chunks = load_markdown_knowledge_base(args.kb)
    kb_meta = [
        (chunk, author_written_variants(chunk), significant_tokens(chunk.title))
        for chunk in chunks
    ]
    n_with_variants = sum(1 for _, variants, _ in kb_meta if variants)

    cases = [
        json.loads(line)
        for line in GOLDEN.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    audit_rows: list[dict] = []
    per_family_added: Counter = Counter()
    total_added = 0
    cases_widened = 0

    for case in cases:
        original = list(case.get("expected_chunk_ids") or [])
        matched, reasons = matching_chunks(case["query"], kb_meta)
        added = sorted(matched - set(original))
        if added:
            cases_widened += 1
            total_added += len(added)
            per_family_added[case.get("family")] += len(added)
            # Giữ nguyên thứ tự gốc, thêm phần mới vào cuối.
            case["expected_chunk_ids"] = original + added
            audit_rows.append(
                {
                    "id": case["id"],
                    "family": case.get("family"),
                    "query": case["query"],
                    "expected_before": original,
                    "added": added,
                    "reasons": {key: reasons[key] for key in added},
                }
            )

    print(f"Đoạn KB có question_variants do người soạn ghi: {n_with_variants}/{len(chunks)}")
    print(f"Tổng case golden: {len(cases)}")
    print(f"Case được mở rộng đáp án mẫu: {cases_widened} ({cases_widened / len(cases):.1%})")
    print(f"Tổng số gán đoạn được thêm: {total_added}")
    print("\nSố gán thêm theo họ câu hỏi:")
    for family, count in per_family_added.most_common():
        print(f"  {family:22s} +{count}")

    # Kiểm chứng bất biến: không được xoá bất kỳ đoạn nào người soạn đã ghi.
    for row in audit_rows:
        case = next(c for c in cases if c["id"] == row["id"])
        missing = set(row["expected_before"]) - set(case["expected_chunk_ids"])
        if missing:
            raise AssertionError(
                f"Case {row['id']} bị mất đáp án mẫu gốc: {missing} — không được phép."
            )
    print("\nBất biến đã kiểm chứng: không case nào mất đáp án mẫu gốc.")

    if args.dry_run:
        print("\n--dry-run: không ghi file.")
        return 0

    GOLDEN.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n",
        encoding="utf-8",
    )
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        json.dumps(
            {
                "method": "union with author-written question_variants and full title match",
                "independent_of_retriever": True,
                "kb_chunks_total": len(chunks),
                "kb_chunks_with_variants": n_with_variants,
                "cases_total": len(cases),
                "cases_widened": cases_widened,
                "assignments_added": total_added,
                "added_by_family": dict(per_family_added),
                "changes": audit_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nĐã ghi {GOLDEN}")
    print(f"Đã ghi bản kiểm toán {AUDIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
