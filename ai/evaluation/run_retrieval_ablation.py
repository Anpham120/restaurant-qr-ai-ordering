"""Run registered retrieval ablations on the dev split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.research_dataset import DatasetSplit  # noqa: E402
from evaluation.run_retrieval_experiment import RetrievalMethod, run_method  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--output",
        type=Path,
        default=AI_ROOT / "evaluation" / "results" / "retrieval_ablation_summary.json",
    )
    args = parser.parse_args()
    split = DatasetSplit.DEV if args.split == "dev" else DatasetSplit.TEST
    rows: list[dict[str, object]] = []
    configs = [
        ("baseline", True, False, "Default hybrid_e5_small with production menu filters"),
        ("no_menu_filter", False, False, "Skip filter_menu_retrieval_results on menu cases"),
        ("with_rerank", True, True, "Cross-encoder rerank on knowledge cases (optional dep)"),
    ]
    for name, apply_menu_filters, with_rerank, note in configs:
        try:
            result = run_method(
                RetrievalMethod.HYBRID_E5_SMALL,
                split=split,
                top_k=args.top_k,
                allow_frozen_test=split is DatasetSplit.TEST,
                apply_menu_filters=apply_menu_filters,
                with_rerank=with_rerank,
            )
            metrics = result.get("metrics", {})
            by_k = metrics.get("by_k") or {}
            at_5 = by_k.get(5) or by_k.get("5") or {}
            rows.append(
                {
                    "ablation": name,
                    "note": note,
                    "mrr_at_5": at_5.get("mrr"),
                    "hit_at_5": at_5.get("hit_rate"),
                    "evaluated_cases": metrics.get("evaluated_cases"),
                    "status": "ok",
                }
            )
        except Exception as exc:  # noqa: BLE001 - ablation runner should continue
            rows.append({"ablation": name, "note": note, "status": "error", "error": str(exc)})
    payload = {"split": args.split, "ablations": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
