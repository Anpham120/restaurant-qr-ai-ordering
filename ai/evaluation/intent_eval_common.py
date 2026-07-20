"""Shared helpers for hybrid intent classification evaluation."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.clients.gemini import GeminiClient
from app.config import AiServiceConfig, load_config
from app.rag.constraint_extractor import extract_constraints
from app.rag.conversation_policy import build_conversation_policy
from app.rag.intent_classifier import classify_intent_with_history
from app.rag.llm_intent_classifier import (
    classify_with_llm,
    is_ambiguous,
    merge_llm_signals_into_constraints,
    merge_llm_signals_into_policy,
)

AI_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = AI_ROOT / "evaluation" / "intent_classification_cases.jsonl"
RESULTS_DIR = AI_ROOT / "evaluation" / "results"

GPT55_MODEL = "cx/gpt-5.5"
DEEPSEEK_MODEL = "oc/deepseek-v4-flash-free"
DEFAULT_MODELS = (GPT55_MODEL, DEEPSEEK_MODEL)


def load_intent_cases(path: Path | None = None) -> list[dict[str, Any]]:
    cases_path = path or CASES_PATH
    return [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def is_holdout_case(case: dict[str, Any]) -> bool:
    """Hold-out split: auto-generated ``gen_*`` cases were not hand-tuned during development."""

    return str(case.get("id", "")).startswith("gen_")


def split_eval_cases(
    cases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dev_cases = [case for case in cases if not is_holdout_case(case)]
    holdout_cases = [case for case in cases if is_holdout_case(case)]
    return dev_cases, holdout_cases


def evaluate_keyword_with_holdout(
    cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report keyword accuracy on full set, dev (hand-written), and hold-out (generated)."""

    all_cases = cases or load_intent_cases()
    dev_cases, holdout_cases = split_eval_cases(all_cases)
    _, all_summary = evaluate_keyword_baseline(all_cases)
    _, dev_summary = evaluate_keyword_baseline(dev_cases)
    _, holdout_summary = evaluate_keyword_baseline(holdout_cases)
    return {
        "split_sizes": {
            "all": len(all_cases),
            "dev_handwritten": len(dev_cases),
            "holdout_generated": len(holdout_cases),
        },
        "all": all_summary,
        "dev_handwritten": dev_summary,
        "holdout_generated": holdout_summary,
    }


def _party(pred: dict[str, Any]) -> int | None:
    party = pred.get("party_size")
    if party is None:
        return None
    return int(party)


def _case_history(case: dict[str, Any]) -> list[dict[str, Any]]:
    history = case.get("history")
    if not history:
        return []
    return list(history)


def keyword_route(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    history = history or []
    constraints = extract_constraints(message, history)
    policy = build_conversation_policy(message, history, "", [])
    return {
        "wants_recommendations": policy.wants_recommendations,
        "party_size": policy.party_size or constraints.get("party_size"),
        "is_solo_dining": bool(constraints.get("is_solo_dining")),
    }


def predict_ambiguous(message: str, history: list[dict[str, Any]] | None = None) -> bool:
    history = history or []
    constraints = extract_constraints(message, history)
    policy = build_conversation_policy(message, history, "", [])
    intent = classify_intent_with_history(message, history)
    return is_ambiguous(intent, constraints, policy, message=message)


def score_routing(pred: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Primary metric: recommendation intent + party size."""
    ok_wants = pred["wants_recommendations"] == expected["expected_wants_recommendations"]
    ok_party = _party(pred) == expected.get("expected_party_size")
    return ok_wants and ok_party


def score_solo_flag(pred: dict[str, Any], expected: dict[str, Any]) -> bool:
    return pred["is_solo_dining"] == expected["expected_is_solo_dining"]


def score_full(pred: dict[str, Any], expected: dict[str, Any]) -> bool:
    return score_routing(pred, expected) and score_solo_flag(pred, expected)


def build_client(config: AiServiceConfig, model: str) -> GeminiClient:
    return GeminiClient(
        config.base_url,
        config.api_key,
        model,
        config.intent_classification_timeout_seconds,
        config.max_retry,
        use_gemini_features=config.uses_gemini_native_features,
    )


async def hybrid_route(
    message: str,
    *,
    client: GeminiClient | None,
    config: AiServiceConfig,
    history: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], float | None, bool]:
    history = history or []
    constraints = extract_constraints(message, history)
    policy = build_conversation_policy(message, history, "", [])
    intent = classify_intent_with_history(message, history)
    ambiguous = is_ambiguous(intent, constraints, policy, message=message)
    latency_ms: float | None = None
    used_llm = False
    if ambiguous and client is not None and config.llm_intent_classification_enabled:
        t0 = time.perf_counter()
        signals = await classify_with_llm(
            client,
            message,
            history,
            "",
            timeout_seconds=config.intent_classification_timeout_seconds,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        used_llm = True
        if signals is not None:
            constraints = merge_llm_signals_into_constraints(constraints, signals)
            policy = merge_llm_signals_into_policy(policy, signals)
    pred = {
        "wants_recommendations": policy.wants_recommendations,
        "party_size": policy.party_size or constraints.get("party_size"),
        "is_solo_dining": bool(constraints.get("is_solo_dining")),
    }
    return pred, latency_ms, used_llm


def _mean(values: list[bool]) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if v) / len(values)


def _latency_stats(latencies: list[float]) -> dict[str, float | None]:
    if not latencies:
        return {"p50_ms": None, "p95_ms": None, "mean_ms": None}
    ordered = sorted(latencies)
    p50 = statistics.median(ordered)
    idx95 = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return {
        "p50_ms": round(p50, 1),
        "p95_ms": round(ordered[idx95], 1),
        "mean_ms": round(statistics.mean(ordered), 1),
    }


def summarize_rows(rows: list[dict[str, Any]], *, prefix: str) -> dict[str, Any]:
    routing_key = f"{prefix}_routing_correct"
    solo_key = f"{prefix}_solo_correct"
    full_key = f"{prefix}_full_correct"
    llm_latencies = [
        float(row["intent_llm_ms"])
        for row in rows
        if row.get("used_llm") and row.get("intent_llm_ms") is not None
    ]

    def _group_summary(group_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(group_rows),
            "routing_accuracy": round(_mean([bool(r[routing_key]) for r in group_rows]), 4),
            "solo_flag_accuracy": round(_mean([bool(r[solo_key]) for r in group_rows]), 4),
            "full_accuracy": round(_mean([bool(r[full_key]) for r in group_rows]), 4),
        }

    by_category: dict[str, dict[str, Any]] = {}
    for category in sorted({str(row["category"]) for row in rows}):
        cat_rows = [row for row in rows if row["category"] == category]
        by_category[category] = _group_summary(cat_rows)

    by_tier: dict[str, dict[str, Any]] = {}
    for tier in sorted({str(row.get("tier", "core")) for row in rows}):
        tier_rows = [row for row in rows if row.get("tier", "core") == tier]
        by_tier[tier] = _group_summary(tier_rows)

    by_language: dict[str, dict[str, Any]] = {}
    for language in sorted({str(row.get("language", "vi")) for row in rows}):
        lang_rows = [row for row in rows if row.get("language", "vi") == language]
        by_language[language] = _group_summary(lang_rows)

    by_llm_expectation: dict[str, dict[str, Any]] = {}
    for label, predicate in (
        ("expects_llm_true", lambda row: row.get("expects_llm") is True),
        ("expects_llm_false", lambda row: row.get("expects_llm") is False),
    ):
        subset = [row for row in rows if predicate(row)]
        if subset:
            by_llm_expectation[label] = _group_summary(subset)

    solo_rows = [row for row in rows if row.get("expected_is_solo_dining")]
    solo_subset = _group_summary(solo_rows) if solo_rows else None

    llm_gate_rows = [row for row in rows if row.get("expects_llm") is not None]
    llm_gate_accuracy: float | None = None
    if llm_gate_rows:
        llm_gate_accuracy = round(
            _mean([bool(row.get("used_llm")) == bool(row.get("expects_llm")) for row in llm_gate_rows]),
            4,
        )

    hybrid_improvement = None
    if prefix == "hybrid":
        flipped = sum(
            1
            for row in rows
            if row.get("hybrid_routing_correct") and not row.get("keyword_routing_correct")
        )
        regressed = sum(
            1
            for row in rows
            if row.get("keyword_routing_correct") and not row.get("hybrid_routing_correct")
        )
        hybrid_improvement = {
            "keyword_to_hybrid_flips": flipped,
            "hybrid_to_keyword_regressions": regressed,
            "net_gain": flipped - regressed,
        }

    return {
        "routing_accuracy": round(_mean([bool(r[routing_key]) for r in rows]), 4),
        "solo_flag_accuracy": round(_mean([bool(r[solo_key]) for r in rows]), 4),
        "full_accuracy": round(_mean([bool(r[full_key]) for r in rows]), 4),
        "llm_call_rate": round(_mean([bool(r.get("used_llm")) for r in rows]), 4),
        "llm_gate_accuracy": llm_gate_accuracy,
        "latency": _latency_stats(llm_latencies),
        "by_category": by_category,
        "by_tier": by_tier,
        "by_language": by_language,
        "by_llm_expectation": by_llm_expectation,
        "solo_subset": solo_subset,
        "hybrid_improvement": hybrid_improvement,
    }


def evaluate_keyword_baseline(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        history = _case_history(case)
        pred = keyword_route(case["message"], history)
        ambiguous = predict_ambiguous(case["message"], history)
        rows.append(
            {
                **case,
                "kw_wants": pred["wants_recommendations"],
                "kw_party": pred["party_size"],
                "kw_solo": pred["is_solo_dining"],
                "predicted_ambiguous": ambiguous,
                "keyword_routing_correct": score_routing(pred, case),
                "keyword_solo_correct": score_solo_flag(pred, case),
                "keyword_full_correct": score_full(pred, case),
            }
        )
    return rows, summarize_rows(rows, prefix="keyword")


async def evaluate_hybrid_model(
    cases: list[dict[str, Any]],
    *,
    model: str,
    config: AiServiceConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    client = build_client(config, model) if config.llm_enabled else None
    rows: list[dict[str, Any]] = []
    for case in cases:
        history = _case_history(case)
        pred, latency_ms, used_llm = await hybrid_route(
            case["message"],
            client=client,
            config=config,
            history=history,
        )
        ambiguous = predict_ambiguous(case["message"], history)
        rows.append(
            {
                **case,
                "model": model,
                "hy_wants": pred["wants_recommendations"],
                "hy_party": pred["party_size"],
                "hy_solo": pred["is_solo_dining"],
                "predicted_ambiguous": ambiguous,
                "hybrid_routing_correct": score_routing(pred, case),
                "hybrid_solo_correct": score_solo_flag(pred, case),
                "hybrid_full_correct": score_full(pred, case),
                "used_llm": used_llm,
                "intent_llm_ms": latency_ms,
            }
        )
    return rows, summarize_rows(rows, prefix="hybrid")


def model_slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def build_head_to_head(
    left_model: str,
    left_rows: list[dict[str, Any]],
    right_model: str,
    right_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    right_by_id = {row["id"]: row for row in right_rows}
    left_wins = 0
    right_wins = 0
    ties = 0
    flips: list[dict[str, Any]] = []
    for left in left_rows:
        right = right_by_id[left["id"]]
        left_ok = bool(left["hybrid_routing_correct"])
        right_ok = bool(right["hybrid_routing_correct"])
        if left_ok and not right_ok:
            left_wins += 1
        elif right_ok and not left_ok:
            right_wins += 1
        else:
            ties += 1
        if left_ok != right_ok:
            flips.append(
                {
                    "id": left["id"],
                    "message": left["message"],
                    "category": left["category"],
                    f"{model_slug(left_model)}_correct": left_ok,
                    f"{model_slug(right_model)}_correct": right_ok,
                }
            )
    left_summary = summarize_rows(left_rows, prefix="hybrid")
    right_summary = summarize_rows(right_rows, prefix="hybrid")
    return {
        "left_model": left_model,
        "right_model": right_model,
        f"{model_slug(left_model)}_routing_accuracy": left_summary["routing_accuracy"],
        f"{model_slug(right_model)}_routing_accuracy": right_summary["routing_accuracy"],
        "routing_accuracy_delta_left_minus_right": round(
            left_summary["routing_accuracy"] - right_summary["routing_accuracy"],
            4,
        ),
        "solo_flag_delta_left_minus_right": round(
            left_summary["solo_flag_accuracy"] - right_summary["solo_flag_accuracy"],
            4,
        ),
        "left_wins": left_wins,
        "right_wins": right_wins,
        "ties": ties,
        "disagreements": flips,
    }


@dataclass(frozen=True)
class IntentEvalReport:
    keyword_rows: list[dict[str, Any]]
    keyword_summary: dict[str, Any]
    model_rows: dict[str, list[dict[str, Any]]]
    model_summaries: dict[str, dict[str, Any]]
    head_to_head: dict[str, Any] | None
    payload: dict[str, Any]


async def run_intent_eval(
    *,
    models: list[str] | None = None,
    cases_path: Path | None = None,
    config: AiServiceConfig | None = None,
) -> IntentEvalReport:
    cases = load_intent_cases(cases_path)
    cfg = config or load_config()
    model_list = models or list(DEFAULT_MODELS)

    keyword_rows, keyword_summary = evaluate_keyword_baseline(cases)

    model_rows: dict[str, list[dict[str, Any]]] = {}
    model_summaries: dict[str, dict[str, Any]] = {}
    for model in model_list:
        rows, summary = await evaluate_hybrid_model(cases, model=model, config=cfg)
        for row, kw_row in zip(rows, keyword_rows):
            row["keyword_routing_correct"] = kw_row["keyword_routing_correct"]
        model_rows[model] = rows
        model_summaries[model] = summarize_rows(rows, prefix="hybrid")

    head_to_head: dict[str, Any] | None = None
    if len(model_list) >= 2:
        head_to_head = build_head_to_head(
            model_list[0],
            model_rows[model_list[0]],
            model_list[1],
            model_rows[model_list[1]],
        )

    payload: dict[str, Any] = {
        "case_count": len(cases),
        "category_count": len({case["category"] for case in cases}),
        "tier_counts": {
            tier: sum(1 for case in cases if case.get("tier") == tier)
            for tier in sorted({case.get("tier", "core") for case in cases})
        },
        "base_url": cfg.base_url,
        "llm_intent_classification_enabled": cfg.llm_intent_classification_enabled,
        "intent_classification_timeout_seconds": cfg.intent_classification_timeout_seconds,
        "keyword_baseline": keyword_summary,
        "models": model_list,
        "model_results": {
            model: {
                "summary": model_summaries[model],
                "cases": model_rows[model],
            }
            for model in model_list
        },
        "head_to_head": head_to_head,
    }
    return IntentEvalReport(
        keyword_rows=keyword_rows,
        keyword_summary=keyword_summary,
        model_rows=model_rows,
        model_summaries=model_summaries,
        head_to_head=head_to_head,
        payload=payload,
    )
