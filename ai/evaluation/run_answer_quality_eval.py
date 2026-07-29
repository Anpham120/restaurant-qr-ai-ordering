# -*- coding: utf-8 -*-
"""Measure answer quality over the golden dev split.

Runs offline by default — no LLM — so it can gate every commit.  Pass
``--live`` to route generation through the configured provider instead; the
deterministic paths answer the same way either way, so the offline run already
covers roughly a third of the set exactly as production would.

    python evaluation/run_answer_quality_eval.py
    python evaluation/run_answer_quality_eval.py --live --output results.json
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from app.config import AiServiceConfig, load_config  # noqa: E402
from app.rag.constraint_extractor import extract_constraints  # noqa: E402
from app.services.assistant import AiAssistantService  # noqa: E402
from evaluation.answer_quality_metrics import score_answer  # noqa: E402
from evaluation.golden_eval_common import load_golden_cases, load_menu_items  # noqa: E402

DEFAULT_OUTPUT = AI_ROOT / "evaluation" / "results" / "answer_quality_eval.json"


def _build_service(live: bool) -> AiAssistantService:
    if live:
        from app.clients.router import RouterClient

        config = dataclasses.replace(
            load_config(), knowledge_base_path=AI_ROOT / "knowledge-base"
        )
        client = RouterClient(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            timeout_seconds=config.llm_timeout_seconds,
            max_retry=config.max_retry,
        )
        return AiAssistantService(config, llm_client=client)

    runtime = load_config()
    config = AiServiceConfig(
        provider="none",
        base_url="",
        api_key="",
        model="offline-answer-quality",
        llm_timeout_seconds=1,
        request_budget_seconds=2,
        max_retry=0,
        max_tokens=700,
        reasoning_effort="low",
        knowledge_base_path=AI_ROOT / "knowledge-base",
        top_k=runtime.top_k,
        retrieval_method=runtime.retrieval_method,
        embedding_model=runtime.embedding_model,
        # The profile decides which deterministic paths run at all, so it has to
        # match the deployment or the whole measurement describes another system.
        pipeline_profile=runtime.pipeline_profile,
        llm_first=runtime.llm_first,
    )
    return AiAssistantService(config, llm_client=None)


async def evaluate(split: str, live: bool) -> dict:
    service = _build_service(live)
    menu_items = load_menu_items()
    cases = load_golden_cases(split)

    rows: list[dict] = []
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
                    "session_id": f"aq-{case['id']}",
                    "session_state": {},
                    "live_context": {
                        "catalog_version": "answer-quality-v1",
                        "menu_items": menu_items,
                        "table_code": "T01",
                    },
                }
            )
        except Exception as error:  # pragma: no cover - reported, never swallowed
            rows.append(
                {
                    "id": case["id"],
                    "family": case.get("family"),
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            continue

        score = score_answer(query, extract_constraints(query), response, menu_items)
        rows.append(
            {
                "id": case["id"],
                "family": case.get("family"),
                "query": query,
                "path": (response.get("latency_ms") or {}).get("path"),
                **score,
            }
        )

    scored = [row for row in rows if "error" in row is False or "usable" in row]
    total = len(scored) or 1
    violations: Counter = Counter()
    for row in scored:
        for kind in row["constraint"]["violations"]:
            violations[kind] += 1

    per_family: dict[str, dict] = defaultdict(lambda: {"total": 0, "usable": 0})
    for row in scored:
        bucket = per_family[str(row.get("family"))]
        bucket["total"] += 1
        bucket["usable"] += int(row["usable"])

    return {
        "split": split,
        "mode": "live" if live else "offline",
        "cases": rows,
        "summary": {
            "scored_cases": len(scored),
            "errors": sum(1 for row in rows if "error" in row),
            "usable_rate": sum(row["usable"] for row in scored) / total,
            "constraint_respect_rate": sum(
                row["constraint"]["respected"] for row in scored
            )
            / total,
            "grounded_rate": sum(row["grounding"]["grounded"] for row in scored) / total,
            "contained_rate": sum(row["containment"]["contained"] for row in scored)
            / total,
            "actionable_rate": sum(row["actionability"]["actionable"] for row in scored)
            / total,
            "deflection_rate": sum(row["deflected"] for row in scored) / total,
            "violations_by_kind": dict(violations),
            "per_family": {
                name: {
                    **bucket,
                    "usable_rate": bucket["usable"] / (bucket["total"] or 1),
                }
                for name, bucket in sorted(per_family.items())
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev")
    parser.add_argument("--live", action="store_true", help="Route generation through the provider.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = asyncio.run(evaluate(args.split, args.live))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = report["summary"]
    print(json.dumps({k: v for k, v in summary.items() if k != "per_family"},
                     ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
