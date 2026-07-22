"""Multi-turn session E2E eval (offline pipeline + optional LLM via 9router).

Validates rolling summary updates and duplicate recommendation avoidance
across scripted multi-turn cases from session_scripts.jsonl and
intent_classification_cases.jsonl (tier=multi_turn).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.golden_eval_common import (  # noqa: E402
    build_llm_service,
    build_offline_service,
    load_menu_items,
)
from evaluation.intent_eval_common import load_intent_cases  # noqa: E402

RESULTS_DIR = AI_ROOT / "evaluation" / "results"
DEFAULT_OUTPUT = RESULTS_DIR / "session_e2e_eval.json"
SESSION_SCRIPTS_PATH = AI_ROOT / "evaluation" / "golden" / "session_scripts.jsonl"


def load_session_scripts() -> list[dict[str, Any]]:
    if not SESSION_SCRIPTS_PATH.is_file():
        return []
    cases: list[dict[str, Any]] = []
    with SESSION_SCRIPTS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


async def _run_scripted_session(
    service: Any,
    case: dict[str, Any],
    menu_items: list[dict[str, Any]],
    *,
    use_llm: bool,
) -> dict[str, Any]:
    turns = list(case.get("turns") or [])
    user_turns = [turn for turn in turns if turn.get("role") == "user"]
    if not user_turns:
        return {"case_id": case.get("id"), "pass_no_duplicate": False, "turns_run": 0}

    history: list[dict[str, str]] = []
    suggested_ids: set[str] = set()
    duplicate_hits = 0
    rolling_summary_seen = False
    paths: list[str | None] = []

    for turn in turns:
        role = str(turn.get("role") or "")
        content = str(turn.get("content") or "").strip()
        if role == "assistant":
            history.append({"role": "assistant", "content": content})
            continue
        if role != "user" or not content:
            continue

        service.invalidate_cache()
        response = await service.chat(
            {
                "message": content,
                "history": list(history),
                "menu_items": menu_items,
                "table_code": "T01",
                "session_id": f"session-{case.get('id')}",
                "excluded_menu_item_ids": sorted(suggested_ids),
            }
        )
        paths.append((response.get("latency_ms") or {}).get("path"))
        rolling_summary_seen = rolling_summary_seen or bool(response.get("updated_rolling_summary"))
        assistant_content = str(response.get("content") or "").strip()
        history.append({"role": "user", "content": content})
        history.append({"role": "assistant", "content": assistant_content or "(no content)"})
        for action in response.get("suggested_cart_actions") or []:
            item_id = str(action.get("menu_item_id") or "")
            if not item_id:
                continue
            if item_id in suggested_ids:
                duplicate_hits += 1
            suggested_ids.add(item_id)

    return {
        "case_id": case.get("id"),
        "category": case.get("category"),
        "tier": case.get("tier"),
        "turns_run": len(user_turns),
        "duplicate_recommendation_count": duplicate_hits,
        "has_rolling_summary": rolling_summary_seen,
        "pass_no_duplicate": duplicate_hits == 0,
        "pass_rolling_summary": rolling_summary_seen,
        "paths": paths,
        "use_llm": use_llm,
        "scripted": True,
    }


async def _run_single_turn_case(
    service: Any,
    case: dict[str, Any],
    menu_items: list[dict[str, Any]],
    *,
    use_llm: bool,
) -> dict[str, Any]:
    history = list(case.get("history") or [])
    message = str(case.get("message") or "").strip()
    suggested_ids: set[str] = set()
    duplicate_hits = 0

    response = await service.chat(
        {
            "message": message,
            "history": history,
            "menu_items": menu_items,
            "table_code": "T01",
            "session_id": f"session-{case.get('id')}",
            "excluded_menu_item_ids": sorted(suggested_ids),
        }
    )
    for action in response.get("suggested_cart_actions") or []:
        item_id = str(action.get("menu_item_id") or "")
        if item_id:
            if item_id in suggested_ids:
                duplicate_hits += 1
            suggested_ids.add(item_id)

    return {
        "case_id": case.get("id"),
        "category": case.get("category"),
        "tier": case.get("tier"),
        "turns_run": 1,
        "duplicate_recommendation_count": duplicate_hits,
        "has_rolling_summary": bool(response.get("updated_rolling_summary")),
        "pass_no_duplicate": duplicate_hits == 0,
        "pass_rolling_summary": bool(response.get("updated_rolling_summary")),
        "path": (response.get("latency_ms") or {}).get("path"),
        "use_llm": use_llm,
        "scripted": False,
    }


async def run_eval(
    *,
    tier: str = "multi_turn",
    limit: int | None = None,
    use_llm: bool = False,
    include_scripts: bool = True,
) -> dict[str, Any]:
    intent_cases = [case for case in load_intent_cases() if case.get("tier") == tier]
    script_cases = load_session_scripts() if include_scripts else []
    cases: list[tuple[str, dict[str, Any]]] = [("script", case) for case in script_cases]
    cases.extend(("intent", case) for case in intent_cases)
    if limit is not None:
        cases = cases[:limit]

    menu_items = load_menu_items()
    service = build_llm_service() if use_llm else build_offline_service("hybrid", "e5_small")

    rows: list[dict[str, Any]] = []
    for kind, case in cases:
        if kind == "script":
            rows.append(await _run_scripted_session(service, case, menu_items, use_llm=use_llm))
        else:
            rows.append(await _run_single_turn_case(service, case, menu_items, use_llm=use_llm))

    scripted = [row for row in rows if row.get("scripted")]
    summary = {
        "evaluated_cases": len(rows),
        "scripted_sessions": len(scripted),
        "mean_turns_run": (
            sum(row.get("turns_run", 0) for row in rows) / len(rows) if rows else None
        ),
        "duplicate_free_rate": (
            sum(1 for row in rows if row["pass_no_duplicate"]) / len(rows) if rows else None
        ),
        "rolling_summary_rate": (
            sum(1 for row in rows if row["pass_rolling_summary"]) / len(rows) if rows else None
        ),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "use_llm": use_llm,
        "summary": summary,
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default="multi_turn")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--no-scripts", action="store_true", help="Skip session_scripts.jsonl")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = asyncio.run(
        run_eval(
            tier=args.tier,
            limit=args.limit,
            use_llm=args.use_llm,
            include_scripts=not args.no_scripts,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
