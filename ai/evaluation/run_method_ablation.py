# -*- coding: utf-8 -*-
"""Disable one method at a time and measure what its absence costs.

A method that cannot be shown to earn its place should not be in the system.  This
runs the golden dev split with each mechanism switched off in turn and reports the
answer-quality metric for each, against the baseline with everything on.

Read the output as: *removing this method changes the numbers by this much*.  A row
whose numbers are identical to the baseline is a method with nothing to show for
itself on this evaluation set — which is a finding about the method, or about the
set, and the report must say which.

Offline by default so it is repeatable and cheap; the deterministic paths behave
identically either way, and they are what is being ablated.

    python evaluation/run_method_ablation.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Iterator
from unittest import mock

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from app.config import AiServiceConfig, load_config  # noqa: E402
from app.rag.constraint_extractor import extract_constraints  # noqa: E402
from app.services.assistant import AiAssistantService  # noqa: E402
from evaluation.answer_quality_metrics import score_answer  # noqa: E402
from evaluation.golden_eval_common import load_golden_cases, load_menu_items  # noqa: E402

DEFAULT_OUTPUT = AI_ROOT / "evaluation" / "results" / "method_ablation.json"


def _off(*targets: str) -> Callable[[], Any]:
    """Patch each target to a no-op that declines to answer."""

    def factory() -> Iterator[None]:
        stack = ExitStack()
        for target in targets:
            stack.enter_context(mock.patch(target, return_value=None))
        return stack

    return factory


def _identity(*targets: str) -> Callable[[], Any]:
    """Patch each filter to return its input unchanged."""

    def factory() -> Iterator[None]:
        stack = ExitStack()
        for target in targets:
            stack.enter_context(
                mock.patch(target, side_effect=lambda items, *a, **k: list(items))
            )
        return stack

    return factory


# Each entry: label -> a callable returning a context manager that disables it.
ABLATIONS: dict[str, Callable[[], Any]] = {
    "allergy_menu_path": _off("app.services.assistant.try_allergy_safe_menu_fast_path"),
    "dish_comparison_path": _off("app.services.assistant.try_dish_comparison_fast_path"),
    "kb_info_path": _off("app.services.assistant.try_kb_info_fast_path"),
    "menu_presence_path": _off("app.services.assistant.try_menu_presence_fast_path"),
    "catalog_path": _off("app.services.assistant._try_catalog_fast_path"),
    "spice_filter": _identity("app.services.assistant.filter_items_by_spice"),
    "budget_filter": _identity("app.services.assistant.filter_items_by_budget"),
    "item_kind_filter": _identity("app.services.assistant.filter_items_by_kind"),
}


def _build_service() -> AiAssistantService:
    runtime = load_config()
    config = AiServiceConfig(
        provider="none",
        base_url="",
        api_key="",
        model="offline-ablation",
        llm_timeout_seconds=1,
        request_budget_seconds=2,
        max_retry=0,
        max_tokens=700,
        reasoning_effort="low",
        knowledge_base_path=AI_ROOT / "knowledge-base",
        top_k=runtime.top_k,
        retrieval_method=runtime.retrieval_method,
        embedding_model=runtime.embedding_model,
        pipeline_profile=runtime.pipeline_profile,
        llm_first=runtime.llm_first,
    )
    return AiAssistantService(config, llm_client=None)


async def _measure(cases: list[dict], menu_items: list[dict]) -> dict[str, Any]:
    service = _build_service()
    usable = respected = grounded = contained = actionable = deflected = 0
    substantive = 0
    violations: dict[str, int] = {}
    deterministic = 0
    scored = 0

    for case in cases:
        service.invalidate_cache()
        query = case["query"]
        try:
            response = await service.chat(
                {
                    "contract_version": "v2",
                    "message": query,
                    "pipeline_profile": service._config.pipeline_profile,
                    "history": [],
                    "session_id": f"abl-{case['id']}",
                    "session_state": {},
                    "live_context": {
                        "catalog_version": "ablation-v1",
                        "menu_items": menu_items,
                        "table_code": "T01",
                    },
                }
            )
        except Exception:
            continue

        score = score_answer(query, extract_constraints(query), response, menu_items)
        scored += 1
        usable += score["usable"]
        respected += score["constraint"]["respected"]
        grounded += score["grounding"]["grounded"]
        contained += score["containment"]["contained"]
        actionable += score["actionability"]["actionable"]
        substantive += score["substance"]["substantive"]
        deflected += score["deflected"]
        for kind in score["constraint"]["violations"]:
            violations[kind] = violations.get(kind, 0) + 1
        path = (response.get("latency_ms") or {}).get("path")
        if path and path not in {"fallback", "fallback_no_llm", "llm"}:
            deterministic += 1

    total = scored or 1
    return {
        "scored": scored,
        "usable_rate": usable / total,
        "constraint_respect_rate": respected / total,
        "grounded_rate": grounded / total,
        "contained_rate": contained / total,
        "actionable_rate": actionable / total,
        "substantive_rate": substantive / total,
        "deflection_rate": deflected / total,
        "deterministic_rate": deterministic / total,
        "violations_by_kind": violations,
    }


async def run(split: str) -> dict[str, Any]:
    cases = load_golden_cases(split)
    menu_items = load_menu_items()

    baseline = await _measure(cases, menu_items)
    results: dict[str, Any] = {"baseline": baseline, "ablations": {}}

    for label, factory in ABLATIONS.items():
        with factory():
            results["ablations"][label] = await _measure(cases, menu_items)
    return results


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = asyncio.run(run(args.split))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    base = report["baseline"]
    keys = ("usable_rate", "substantive_rate", "constraint_respect_rate", "deterministic_rate")
    print(f"{'phuong phap bi tat':26}" + "".join(f"{k.replace('_rate',''):>22}" for k in keys))
    print("-" * (26 + 22 * len(keys)))
    print(f"{'(khong tat gi)':26}" + "".join(f"{_fmt(base[k]):>22}" for k in keys))
    for label, metrics in report["ablations"].items():
        cells = []
        for k in keys:
            delta = metrics[k] - base[k]
            mark = "" if abs(delta) < 1e-9 else f" ({delta:+.4f})"
            cells.append(f"{_fmt(metrics[k])}{mark}".rjust(22))
        print(f"{label:26}" + "".join(cells))
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
