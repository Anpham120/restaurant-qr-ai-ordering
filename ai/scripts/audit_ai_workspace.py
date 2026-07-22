"""Audit AI workspace: canonical artifacts, notebook refs, stale files."""

from __future__ import annotations

import json
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
RESULTS = AI_ROOT / "evaluation" / "results"

CANONICAL = {
    "gpt_gate": RESULTS / "golden_llm_eval_cx_gpt55_v3_full_v3b.json",
    "deepseek_sweep": RESULTS / "golden_llm_eval_deepseek_v4_full.json",
    "golden_chat_e2e": RESULTS / "golden_chat_e2e.json",
    "dev_retrieval_summary": RESULTS / "dev_retrieval_summary.v3.json",
    "dev_retrieval_comparison": RESULTS / "dev_retrieval_comparison.v3.json",
    "ci_baseline": RESULTS / "ci_baseline.json",
}

STALE_CANDIDATES = [
    RESULTS / "golden_llm_eval_cx_gpt55_v3_full_v3.json",
    RESULTS / "golden_llm_eval_cx_gpt55_v3_full_v2.json",
    RESULTS / "golden_llm_eval_cx_gpt55_v3_full_rerun.json",
    RESULTS / "golden_llm_eval_cx_gpt55_pilot30_v2.json",
    RESULTS / "golden_llm_eval_cx_gpt55_pilot30_post_routing.json",
    RESULTS / "golden_llm_eval_cx_gpt55_full_v2.log",
    RESULTS / "golden_llm_eval_cx_gpt55_full_run.log",
    RESULTS / "golden_llm_eval_cx_gpt55_v3_full.json",
    RESULTS / "golden_llm_eval_deepseek_v4_flash_v3_full.json",
    RESULTS / "golden_llm_eval.json",
    AI_ROOT / "evaluation" / "golden_questions.csv",
    AI_ROOT / "_fix_fstring.py",
    AI_ROOT / "_fix_notebook_narrative.py",
    AI_ROOT / "_fix_summary.py",
    AI_ROOT / "_fix_arch.py",
    AI_ROOT / "_add_comments.py",
    AI_ROOT / "_rebuild_reorder.py",
    AI_ROOT / "_full_pipeline.py",
    AI_ROOT / "_check.py",
    AI_ROOT / "evaluation" / "run_dual_model_eval.py",
    AI_ROOT / "scripts" / "run_intent_classification_eval.py",
    AI_ROOT / "notebooks" / "rag_retrieval_research.executed.ipynb",
]


def load_summary(path: Path) -> dict | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "summary" not in data:
        return {"exists": True}
    summary = dict(data.get("summary") or {})
    llm = data.get("llm")
    if isinstance(llm, dict):
        summary["model"] = llm.get("model", path.stem)
    return summary


def main() -> int:
    canonical_status = {}
    for name, path in CANONICAL.items():
        summary = load_summary(path) if path.suffix == ".json" else None
        canonical_status[name] = {
            "path": str(path.relative_to(AI_ROOT.parent)),
            "exists": path.is_file(),
            "composite_pass_rate": (summary or {}).get("composite_pass_rate"),
            "model": (summary or {}).get("model"),
        }

    stale_present = [str(p.relative_to(AI_ROOT.parent)) for p in STALE_CANDIDATES if p.is_file()]

    notebook = AI_ROOT / "notebooks" / "rag_retrieval_research.ipynb"
    nb_text = notebook.read_text(encoding="utf-8") if notebook.is_file() else ""
    refs_ok = all(
        name in nb_text
        for name in (
            "golden_llm_eval_cx_gpt55_v3_full_v3b.json",
            "golden_llm_eval_deepseek_v4_full.json",
        )
    )

    print(
        json.dumps(
            {
                "canonical": canonical_status,
                "stale_present": len(stale_present),
                "notebook_refs_ok": refs_ok,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
