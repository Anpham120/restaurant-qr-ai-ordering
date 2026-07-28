"""Run the same full-system sample through GPT-5.5 and DeepSeek via 9router.

Outputs are isolated under ``results/dual_model/<run_id>`` so a smoke run can
never overwrite approved full-evaluation artifacts.  The comparison contains
aggregate counts only; API keys, prompts, and answer bodies are not copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
RESULTS_DIR = AI_ROOT / "evaluation" / "results"
sys.path.insert(0, str(AI_ROOT))

from evaluation.dual_model_comparison import compare_model_artifacts  # noqa: E402
from evaluation.golden_eval_common import (  # noqa: E402
    DEFAULT_STRATIFIED_SAMPLING_SEED,
    load_golden_cases,
    summarize_case_sample,
)
from evaluation.run_golden_llm_eval import main as run_golden_llm_eval_main  # noqa: E402


PROFILES = {
    "gpt55": {"model": "cx/gpt-5.5", "file": "gpt55.json"},
    "deepseek": {
        "model": "oc/deepseek-v4-flash-free",
        "file": "deepseek.json",
    },
    "luna": {
        "model": "cx/gpt-5.6-luna-review",
        "file": "luna.json",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    sample_protocol = _sampling_protocol(args)
    run_id = _safe_run_id(args.run_id)
    output_dir = args.output_dir or RESULTS_DIR / "dual_model" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = _now()
    artifacts: dict[str, dict[str, Any]] = {}
    artifact_meta: dict[str, dict[str, Any]] = {}
    exit_codes: dict[str, int] = {}
    # Keep routing/evidence deterministic. The compared model is used only for
    # generation, not as an upstream intent classifier.
    os.environ["AI_LLM_INTENT_CLASSIFICATION_ENABLED"] = "false"

    for profile_name in args.profiles:
        profile = PROFILES[profile_name]
        output = output_dir / profile["file"]
        os.environ["LLM_PROVIDER"] = "9router"
        os.environ["LLM_MODEL"] = profile["model"]
        eval_args = _build_eval_args(args, output=output)
        print(f"profile={profile_name} model={profile['model']} gateway=9router")
        try:
            code = int(run_golden_llm_eval_main(eval_args))
        except Exception as exc:  # keep the comparison secret-safe on config/provider failure
            code = 2
            print(f"profile={profile_name} status=FAIL error_type={type(exc).__name__}")
        exit_codes[profile_name] = code
        if output.is_file():
            payload = json.loads(output.read_text(encoding="utf-8"))
            artifacts[profile_name] = payload
            artifact_meta[profile_name] = {
                "path": str(output.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }

    actual_sample_hashes = {
        profile: (payload.get("dataset") or {}).get("sampling") or {}
        for profile, payload in artifacts.items()
    }
    sample_matches = bool(actual_sample_hashes) and len(actual_sample_hashes) == len(args.profiles) and all(
        metadata.get("case_set_sha256") == sample_protocol["case_set_sha256"]
        and metadata.get("case_order_sha256") == sample_protocol["case_order_sha256"]
        for metadata in actual_sample_hashes.values()
    )

    comparison = compare_model_artifacts(artifacts)
    comparison.update(
        {
            "run_id": run_id,
            "started_at_utc": started_at,
            "finished_at_utc": _now(),
            "protocol": {
                "split": args.split,
                "limit": args.limit,
                "families": args.families or "all",
                "sleep_ms": args.sleep_ms,
                "max_retry": args.max_retry,
                "same_evidence_prompt_and_budget": bool(
                    (comparison.get("generation_input_parity") or {}).get("pass")
                ),
                "llm_intent_classification_enabled": False,
                **sample_protocol,
                "same_case_ids_and_order": sample_matches,
            },
            "artifacts": artifact_meta,
            "profile_exit_codes": exit_codes,
        }
    )
    all_profiles_ran = set(artifacts) == set(args.profiles)
    every_model_reached_provider = bool(comparison.get("models")) and all(
        ((row.get("availability") or {}).get("numerator") or 0) > 0
        for row in comparison.get("models") or []
    )
    pipeline_fidelity = _retrieval_pipeline_fidelity(comparison)
    comparison["pipeline_fidelity"] = pipeline_fidelity
    generation_fidelity = _generation_input_fidelity(comparison)
    comparison["generation_fidelity"] = generation_fidelity
    comparison["smoke_pass"] = bool(
        all_profiles_ran
        and sample_matches
        and comparison.get("comparison_status") == "comparable"
        and every_model_reached_provider
        and pipeline_fidelity["pass"]
        and generation_fidelity["pass"]
    )
    comparison_path = output_dir / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"comparison={comparison_path}")
    for row in comparison.get("models") or []:
        availability = row.get("availability") or {}
        quality = row.get("quality_on_success") or {}
        print(
            f"model={row.get('model')} "
            f"availability={availability.get('numerator')}/{availability.get('denominator')} "
            f"quality_on_success={quality.get('numerator')}/{quality.get('denominator')}"
        )
    print(f"smoke_pass={comparison['smoke_pass']}")
    return 0 if comparison["smoke_pass"] else 3


def _retrieval_pipeline_fidelity(comparison: dict[str, Any]) -> dict[str, bool]:
    """Reject a nominal hybrid comparison that silently ran on a fallback."""

    runtime = comparison.get("retriever_runtime") or {}
    by_profile = runtime.get("by_profile") or {}
    profiles = [value for value in by_profile.values() if isinstance(value, dict)]
    same_runtime = bool(runtime.get("same_runtime")) and bool(profiles)
    no_fallback = bool(profiles) and not bool(runtime.get("fallback_present")) and all(
        not bool(profile.get("fallback_used")) for profile in profiles
    )
    requested_matches_effective = bool(profiles) and all(
        str(profile.get("requested_method") or "")
        == str(profile.get("effective_method") or "")
        for profile in profiles
    )
    return {
        "same_runtime": same_runtime,
        "no_fallback": no_fallback,
        "requested_matches_effective": requested_matches_effective,
        "pass": bool(same_runtime and no_fallback and requested_matches_effective),
    }


def _generation_input_fidelity(comparison: dict[str, Any]) -> dict[str, Any]:
    """Require all paired provider calls to share exact prompt/evidence and budget."""

    parity = comparison.get("generation_input_parity") or {}
    return {
        "common_llm_called_pair_count": int(
            parity.get("common_llm_called_pair_count") or 0
        ),
        "matching_pair_count": int(parity.get("matching_pair_count") or 0),
        "same_generation_config": bool(parity.get("same_generation_config")),
        "pass": bool(parity.get("pass")),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=tuple(PROFILES),
        default=["gpt55", "deepseek"],
    )
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--families", default="")
    parser.add_argument(
        "--sampling-strategy",
        choices=("head", "stratified"),
        default="stratified",
        help="Use balanced family/intent sampling for a fair model comparison",
    )
    parser.add_argument(
        "--sampling-seed",
        type=int,
        default=DEFAULT_STRATIFIED_SAMPLING_SEED,
    )
    parser.add_argument("--sleep-ms", type=int, default=1500)
    parser.add_argument("--max-retry", type=int, default=1)
    parser.add_argument("--run-id", default=_default_run_id())
    parser.add_argument("--output-dir", type=Path)
    return parser


def _build_eval_args(args: argparse.Namespace, *, output: Path | str) -> list[str]:
    eval_args = [
        "--split",
        args.split,
        "--limit",
        str(args.limit),
        "--sampling-strategy",
        args.sampling_strategy,
        "--sampling-seed",
        str(args.sampling_seed),
        "--sleep-ms",
        str(args.sleep_ms),
        "--max-retry",
        str(args.max_retry),
        "--output",
        str(output),
    ]
    if args.families:
        eval_args.extend(["--families", args.families])
    return eval_args


def _sampling_protocol(args: argparse.Namespace) -> dict[str, Any]:
    families = {item.strip() for item in args.families.split(",") if item.strip()} or None
    cases = load_golden_cases(
        None if args.split == "all" else args.split,
        families=families,
        limit=args.limit,
        sampling_strategy=args.sampling_strategy,
        sampling_seed=args.sampling_seed,
    )
    summary = summarize_case_sample(
        cases,
        sampling_strategy=args.sampling_strategy,
        sampling_seed=args.sampling_seed if args.sampling_strategy == "stratified" else None,
    )
    return {
        "sampling_strategy": summary["strategy"],
        "sampling_seed": summary["seed"],
        "family_distribution": summary["family_distribution"],
        "intent_distribution": summary["intent_distribution"],
        "case_set_sha256": summary["case_set_sha256"],
        "case_order_sha256": summary["case_order_sha256"],
    }


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_run_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    if not safe:
        raise ValueError("run_id must contain at least one safe character")
    return safe[:80]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
