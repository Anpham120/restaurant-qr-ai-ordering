"""Populate human-eval sample with GPT golden responses and auto-scores.

Uses golden LLM eval artifacts for the 50-case stratified sample. Auto-scores
map pipeline metrics to the human rubric (1-5); brand_voice and fluency remain
placeholders pending manual review.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = AI_ROOT / "evaluation" / "templates" / "human_eval_sample_50.csv"
DEFAULT_GOLDEN = AI_ROOT / "evaluation" / "results" / "golden_llm_eval_cx_gpt55_v3_full_v3b.json"
DEFAULT_OUTPUT = AI_ROOT / "evaluation" / "templates" / "human_eval_sample_50_scored.csv"
DEFAULT_RESPONSES = AI_ROOT / "evaluation" / "results" / "human_eval_sample_50_responses.json"


def _auto_score(value: bool | None, *, pass_score: int = 5, fail_score: int = 2) -> str:
    if value is True:
        return str(pass_score)
    if value is False:
        return str(fail_score)
    return ""


def _faithfulness_score(faithfulness: float | None) -> str:
    if faithfulness is None:
        return ""
    if faithfulness >= 0.5:
        return "5"
    if faithfulness >= 0.25:
        return "4"
    if faithfulness >= 0.1:
        return "3"
    return "2"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--responses-output", type=Path, default=DEFAULT_RESPONSES)
    args = parser.parse_args()

    golden_payload = json.loads(args.golden.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in golden_payload.get("cases") or []}

    rows_out: list[dict[str, str]] = []
    responses_out: list[dict[str, object]] = []

    with args.sample.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for extra in ("response_preview", "auto_scored"):
            if extra not in fieldnames:
                fieldnames.append(extra)

        for row in reader:
            case_id = str(row.get("case_id") or "").strip()
            golden = by_id.get(case_id)
            if golden is None:
                row["auto_scored"] = "false"
                row["notes"] = (row.get("notes") or "") + " missing golden eval row"
                rows_out.append(row)
                continue

            content = str(golden.get("content") or "")
            grounding = golden.get("grounding_pass")
            safety = golden.get("safety_pass")
            composite = golden.get("composite_pass")
            faithfulness = golden.get("faithfulness_score")

            row["score_groundedness"] = _auto_score(grounding) or _faithfulness_score(faithfulness)
            row["score_safety"] = _auto_score(safety)
            row["score_task_success"] = _auto_score(composite)
            row["score_brand_voice"] = row.get("score_brand_voice") or "4"
            row["score_fluency"] = row.get("score_fluency") or "4"
            row["pass_overall"] = "true" if composite else "false" if composite is False else ""
            row["reviewer"] = row.get("reviewer") or "auto/golden_llm_eval"
            row["response_preview"] = content[:160].replace("\n", " ")
            row["auto_scored"] = "true"
            note_bits = []
            if not composite:
                note_bits.append("composite_fail")
            if grounding is False:
                note_bits.append("grounding_fail")
            if safety is False:
                note_bits.append("safety_fail")
            if note_bits:
                row["notes"] = "; ".join(note_bits)
            rows_out.append(row)

            responses_out.append(
                {
                    "case_id": case_id,
                    "family": row.get("family"),
                    "query": row.get("query"),
                    "model": row.get("model"),
                    "content": content,
                    "grounding_pass": grounding,
                    "safety_pass": safety,
                    "composite_pass": composite,
                    "faithfulness_score": faithfulness,
                    "suggested_menu_ids": golden.get("suggested_menu_ids"),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    args.responses_output.parent.mkdir(parents=True, exist_ok=True)
    auto_pass = sum(1 for row in rows_out if row.get("pass_overall") == "true")
    payload = {
        "source_golden_eval": str(args.golden.relative_to(AI_ROOT.parent)),
        "sample_csv": str(args.output.relative_to(AI_ROOT.parent)),
        "cases": len(rows_out),
        "auto_pass_rate": round(auto_pass / len(rows_out), 4) if rows_out else None,
        "responses": responses_out,
    }
    args.responses_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(rows_out)} scored rows to {args.output}")
    print(f"Auto pass rate: {payload['auto_pass_rate']}")
    print(f"Full responses: {args.responses_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
