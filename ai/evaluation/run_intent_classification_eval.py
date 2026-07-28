"""Evaluate hybrid intent classification on labeled cases; compare multiple LLM models.

Usage:
    py -m evaluation.run_intent_classification_eval
    py -m evaluation.run_intent_classification_eval --models cx/gpt-5.5 oc/deepseek-v4-flash-free
    py -m evaluation.run_intent_classification_eval --output evaluation/results/intent_classification_eval_comparison.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.intent_eval_common import (  # noqa: E402
    CASES_PATH,
    DEFAULT_MODELS,
    RESULTS_DIR,
    model_slug,
    run_intent_eval,
)


def _print_summary(report_payload: dict) -> None:
    kb = report_payload["keyword_baseline"]
    print(f"Cases: {report_payload['case_count']}")
    print(
        "Keyword baseline — routing: "
        f"{kb['routing_accuracy']:.1%}, solo: {kb['solo_flag_accuracy']:.1%}, "
        f"full: {kb['full_accuracy']:.1%}"
    )
    if kb.get("solo_subset"):
        ss = kb["solo_subset"]
        print(f"  Solo subset ({ss['count']} cases): routing {ss['routing_accuracy']:.1%}")
    if kb.get("llm_gate_accuracy") is not None:
        print(f"  LLM gate accuracy (keyword path): {kb['llm_gate_accuracy']:.1%}")
    if kb.get("by_language"):
        langs = ", ".join(
            f"{lang}={data['routing_accuracy']:.1%}"
            for lang, data in kb["by_language"].items()
        )
        print(f"  By language: {langs}")
    for model in report_payload["models"]:
        summary = report_payload["model_results"][model]["summary"]
        lat = summary["latency"]
        p50 = lat["p50_ms"]
        p95 = lat["p95_ms"]
        lat_text = f"p50={p50:.0f}ms p95={p95:.0f}ms" if p50 is not None else "no LLM calls"
        print(
            f"[{model}] hybrid routing: {summary['routing_accuracy']:.1%}, "
            f"solo: {summary['solo_flag_accuracy']:.1%}, "
            f"LLM rate: {summary['llm_call_rate']:.1%}, gate: "
            f"{summary.get('llm_gate_accuracy', 0):.1%}, {lat_text}"
        )
        imp = summary.get("hybrid_improvement")
        if imp:
            print(
                f"  vs keyword: +{imp['keyword_to_hybrid_flips']} flips, "
                f"-{imp['hybrid_to_keyword_regressions']} regressions, "
                f"net {imp['net_gain']:+d}"
            )
    h2h = report_payload.get("head_to_head")
    if h2h:
        print(
            f"Head-to-head ({h2h['left_model']} vs {h2h['right_model']}): "
            f"Δrouting={h2h['routing_accuracy_delta_left_minus_right']:+.1%}, "
            f"{h2h['left_wins']} wins / {h2h['right_wins']} losses / {h2h['ties']} ties"
        )


def _json_default(value: object) -> object:
    if isinstance(value, float) and value != value:
        return None
    return str(value)


async def main_async(args: argparse.Namespace) -> int:
    report = await run_intent_eval(models=args.models, cases_path=args.cases)
    payload = {
        **report.payload,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = args.output or (RESULTS_DIR / "intent_classification_eval_comparison.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    for model in payload["models"]:
        per_model_path = RESULTS_DIR / f"intent_classification_eval_{model_slug(model)}.json"
        per_model_payload = {
            "evaluated_at": payload["evaluated_at"],
            "model": model,
            "case_count": payload["case_count"],
            "base_url": payload["base_url"],
            "keyword_baseline": payload["keyword_baseline"],
            **payload["model_results"][model],
        }
        per_model_path.write_text(
            json.dumps(per_model_payload, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

    _print_summary(payload)
    print(f"Saved comparison: {out_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help=f"Models to compare (default: {', '.join(DEFAULT_MODELS)})",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=CASES_PATH,
        help="Path to labeled JSONL cases",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Combined comparison JSON output path",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
