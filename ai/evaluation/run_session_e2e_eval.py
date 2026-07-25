"""Multi-turn session E2E eval (offline pipeline + optional LLM via 9router).

Validates rolling summary updates and duplicate recommendation avoidance
across scripted multi-turn cases from session_scripts.jsonl and
intent_classification_cases.jsonl (tier=multi_turn).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
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


def build_extended_session_cases(
    *,
    count: int = 50,
    turns: int = 12,
) -> list[dict[str, Any]]:
    """Build deterministic long-session probes without fabricating results."""

    if count < 1:
        return []
    if not 12 <= turns <= 20:
        raise ValueError("extended sessions must contain 12 to 20 user turns")
    cases: list[dict[str, Any]] = []
    tail = [
        "Còn lựa chọn nào phù hợp hơn?",
        "Cái đó bao nhiêu tiền?",
        "Nhắc lại ngân sách và số người giúp mình",
        "Món đó còn bán không?",
        "Còn món khác không?",
        "Cho mình xem thêm đồ uống",
        "Quay lại món đó, giá bao nhiêu?",
        "Tóm tắt các ràng buộc của mình",
    ]
    for index in range(count):
        party_size = 4 + index % 5
        budget_thousands = 550 + (index % 6) * 50
        messages = [
            f"Gợi ý 4 món cho {party_size} người dưới {budget_thousands}k",
            "Cái đó bao nhiêu tiền?",
            "Còn món khác không?",
            "Món đó có đậu phộng không?",
            "Vậy gợi ý món khác không có đậu phộng",
            f"Ngân sách cũ còn đủ cho {party_size} người không?",
            "Còn món khác?",
            "Cái đó bao nhiêu tiền?",
            "Không lấy món vừa rồi",
            "Gợi ý đồ uống khác",
            "Nhà hàng có wifi không?",
            "Quay lại món đó, bao nhiêu tiền?",
        ]
        while len(messages) < turns:
            messages.append(tail[(len(messages) - 12 + index) % len(tail)])
        cases.append(
            {
                "id": f"extended_{index + 1:03d}",
                "category": "typed_context_long_session",
                "tier": "multi_turn_v2",
                "messages": messages,
                "expected_constraints": {
                    "party_size": party_size,
                    "budget_vnd": budget_thousands * 1000,
                },
            }
        )
    return cases


async def _run_extended_session(
    service: Any,
    case: dict[str, Any],
    menu_items: list[dict[str, Any]],
    *,
    use_llm: bool,
) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "facts": [],
        "constraints": {},
        "referenced_menu_item_ids": [],
        "suggested_menu_item_ids": [],
        "rejected_menu_item_ids": [],
        "accepted_menu_item_ids": [],
        "added_to_cart_menu_item_ids": [],
        "rolling_summary": "",
        "memory_version": "v2",
    }
    available_ids = {
        str(item.get("id") or "")
        for item in menu_items
        if item.get("id") and bool(item.get("is_available", True))
    }
    duplicate_count = 0
    invalid_action_count = 0
    context_passes = 0
    context_checks = 0
    referent_passes = 0
    referent_checks = 0
    allergy_fail_closed = False
    paths: list[str | None] = []
    max_history_turns_sent = 0
    expected = dict(case.get("expected_constraints") or {})
    turn_trace: list[dict[str, Any]] = []

    for turn_index, message in enumerate(case.get("messages") or []):
        history_window = history[-12:]
        max_history_turns_sent = max(max_history_turns_sent, len(history_window))
        prior_suggested = set(state.get("suggested_menu_item_ids") or [])
        prior_rejected = set(state.get("rejected_menu_item_ids") or [])
        service.invalidate_cache()
        response = await service.chat(
            {
                "contract_version": "v2",
                "message": message,
                "history": history_window,
                "session_id": f"session-{case.get('id')}",
                "session_state": state,
                "live_context": {
                    "catalog_version": "research-menu-v1",
                    "menu_items": menu_items,
                    "table_code": "T01",
                },
            }
        )
        paths.append((response.get("latency_ms") or {}).get("path"))
        actions = list(response.get("suggested_cart_actions") or [])
        action_ids = {
            str(action.get("menu_item_id") or "")
            for action in actions
            if action.get("menu_item_id")
        }
        duplicate_count += len(action_ids & prior_suggested)
        invalid_action_count += len(
            {
                item_id
                for item_id in action_ids
                if item_id not in available_ids or item_id in prior_rejected
            }
        )

        updates = dict(response.get("session_updates") or {})
        state = {
            "facts": list(updates.get("facts") or state.get("facts") or []),
            "constraints": dict(
                updates.get("constraints") or state.get("constraints") or {}
            ),
            "referenced_menu_item_ids": list(
                updates.get("referenced_menu_item_ids")
                or state.get("referenced_menu_item_ids")
                or []
            ),
            "suggested_menu_item_ids": list(
                updates.get("suggested_menu_item_ids")
                or state.get("suggested_menu_item_ids")
                or []
            ),
            "rejected_menu_item_ids": list(
                updates.get("rejected_menu_item_ids")
                or state.get("rejected_menu_item_ids")
                or []
            ),
            "accepted_menu_item_ids": list(
                updates.get("accepted_menu_item_ids")
                or state.get("accepted_menu_item_ids")
                or []
            ),
            "added_to_cart_menu_item_ids": list(
                updates.get("added_to_cart_menu_item_ids")
                or state.get("added_to_cart_menu_item_ids")
                or []
            ),
            "rolling_summary": str(
                updates.get("rolling_summary")
                or response.get("updated_rolling_summary")
                or state.get("rolling_summary")
                or ""
            ),
            "memory_version": str(updates.get("memory_version") or "v2"),
        }

        for key, value in expected.items():
            context_checks += 1
            if state["constraints"].get(key) == value:
                context_passes += 1

        normalized_message = message.casefold()
        if "bao nhiêu" in normalized_message and "giá" in normalized_message or "bao nhiêu tiền" in normalized_message:
            referent_checks += 1
            decision = response.get("decision") or {}
            cited_ids = {
                str(item.get("menu_item_id") or "")
                for item in response.get("evidence") or []
                if item.get("menu_item_id")
            }
            if decision.get("evidence_sufficient") is True and bool(cited_ids):
                referent_passes += 1

        if turn_index == 3:
            decision = response.get("decision") or {}
            verified_claims = response.get("claims") or []
            allergy_fail_closed = (
                decision.get("evidence_sufficient") is False
                or (
                    bool(verified_claims)
                    and all(bool(claim.get("verified")) for claim in verified_claims)
                    and "ALLERGY_DISCLAIMER" in (response.get("guardrail_flags") or [])
                )
            )

        turn_trace.append(
            {
                "turn": turn_index + 1,
                "message": message,
                "path": paths[-1],
                "action_ids": sorted(action_ids),
                "prior_suggested_ids": sorted(prior_suggested),
                "repeated_action_ids": sorted(action_ids & prior_suggested),
                "decision": response.get("decision") or {},
            }
        )

        history.extend(
            [
                {"role": "user", "content": message},
                {
                    "role": "assistant",
                    "content": str(response.get("content") or ""),
                    "suggested_cart_actions": actions,
                },
            ]
        )

    return {
        "case_id": case.get("id"),
        "category": case.get("category"),
        "tier": case.get("tier"),
        "turns_run": len(case.get("messages") or []),
        "context_checks": {"numerator": context_passes, "denominator": context_checks},
        "referent_checks": {"numerator": referent_passes, "denominator": referent_checks},
        "duplicate_recommendation_count": duplicate_count,
        "invalid_action_count": invalid_action_count,
        "allergy_fail_closed": allergy_fail_closed,
        "max_history_turns_sent": max_history_turns_sent,
        "has_rolling_summary": bool(state.get("rolling_summary")),
        "pass_no_duplicate": duplicate_count == 0,
        "pass_rolling_summary": bool(state.get("rolling_summary")),
        "paths": paths,
        "turn_trace": turn_trace,
        "final_state": state,
        "use_llm": use_llm,
        "scripted": True,
        "extended": True,
    }


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
    extended_session_count: int = 50,
    extended_turns: int = 12,
    retrieval_method: str = "bm25",
) -> dict[str, Any]:
    intent_cases = [case for case in load_intent_cases() if case.get("tier") == tier]
    script_cases = load_session_scripts() if include_scripts else []
    cases: list[tuple[str, dict[str, Any]]] = [("script", case) for case in script_cases]
    cases.extend(("intent", case) for case in intent_cases)
    cases.extend(
        ("extended", case)
        for case in build_extended_session_cases(
            count=extended_session_count,
            turns=extended_turns,
        )
    )
    if limit is not None:
        cases = cases[:limit]

    menu_items = load_menu_items()
    service = (
        build_llm_service(retrieval_method=retrieval_method)
        if use_llm
        else build_offline_service(retrieval_method, "e5_small")
    )

    rows: list[dict[str, Any]] = []
    for kind, case in cases:
        if kind == "script":
            rows.append(await _run_scripted_session(service, case, menu_items, use_llm=use_llm))
        elif kind == "extended":
            rows.append(await _run_extended_session(service, case, menu_items, use_llm=use_llm))
        else:
            rows.append(await _run_single_turn_case(service, case, menu_items, use_llm=use_llm))

    scripted = [row for row in rows if row.get("scripted")]
    extended = [row for row in rows if row.get("extended")]
    context_numerator = sum(row["context_checks"]["numerator"] for row in extended)
    context_denominator = sum(row["context_checks"]["denominator"] for row in extended)
    referent_numerator = sum(row["referent_checks"]["numerator"] for row in extended)
    referent_denominator = sum(row["referent_checks"]["denominator"] for row in extended)
    summary = {
        "evaluated_cases": len(rows),
        "scripted_sessions": len(scripted),
        "extended_sessions": len(extended),
        "extended_turns_min": min((row["turns_run"] for row in extended), default=None),
        "extended_turns_max": max((row["turns_run"] for row in extended), default=None),
        "mean_turns_run": (
            sum(row.get("turns_run", 0) for row in rows) / len(rows) if rows else None
        ),
        "duplicate_free_rate": (
            sum(1 for row in rows if row["pass_no_duplicate"]) / len(rows) if rows else None
        ),
        "rolling_summary_rate": (
            sum(1 for row in rows if row["pass_rolling_summary"]) / len(rows) if rows else None
        ),
        "context_retention": {
            "numerator": context_numerator,
            "denominator": context_denominator,
            "rate": context_numerator / context_denominator if context_denominator else None,
        },
        "referent_resolution": {
            "numerator": referent_numerator,
            "denominator": referent_denominator,
            "rate": referent_numerator / referent_denominator if referent_denominator else None,
        },
        "duplicate_free_extended": {
            "numerator": sum(
                1 for row in extended if row["duplicate_recommendation_count"] == 0
            ),
            "denominator": len(extended),
        },
        "valid_action_extended": {
            "numerator": sum(1 for row in extended if row["invalid_action_count"] == 0),
            "denominator": len(extended),
        },
        "allergy_fail_closed": {
            "numerator": sum(1 for row in extended if row["allergy_fail_closed"]),
            "denominator": len(extended),
        },
    }
    return {
        "protocol_version": "session-e2e-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "use_llm": use_llm,
        "provenance": {
            "commit_sha": _git_sha(),
            "corpus_sha256": _knowledge_corpus_hash(),
            "session_matrix_sha256": hashlib.sha256(
                json.dumps(
                    [case for kind, case in cases if kind == "extended"],
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
            "retrieval_method": retrieval_method,
        },
        "summary": summary,
        "cases": rows,
    }


def _knowledge_corpus_hash() -> str:
    manifest_path = RESULTS_DIR / "knowledge_manifest.json"
    if not manifest_path.is_file():
        return "unknown"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return str(payload.get("corpus_sha256") or "unknown")


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", default="multi_turn")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--no-scripts", action="store_true", help="Skip session_scripts.jsonl")
    parser.add_argument("--extended-sessions", type=int, default=50)
    parser.add_argument("--extended-turns", type=int, default=12)
    parser.add_argument("--retrieval-method", choices=("bm25", "dense", "hybrid"), default="bm25")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = asyncio.run(
        run_eval(
            tier=args.tier,
            limit=args.limit,
            use_llm=args.use_llm,
            include_scripts=not args.no_scripts,
            extended_session_count=args.extended_sessions,
            extended_turns=args.extended_turns,
            retrieval_method=args.retrieval_method,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
