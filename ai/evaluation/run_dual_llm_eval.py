"""Run dual-model golden LLM eval profiles via 9router."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.run_golden_llm_eval import main as run_golden_llm_eval_main  # noqa: E402

PROFILES = {
    "gpt55": {
        "model": "cx/gpt-5.5",
        "output": str(AI_ROOT / "evaluation" / "results" / "golden_llm_eval_cx_gpt55_v3_full_v3b.json"),
    },
    "deepseek": {
        "model": "oc/deepseek-v4-flash-free",
        "output": str(AI_ROOT / "evaluation" / "results" / "golden_llm_eval_deepseek_v4_full.json"),
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=tuple(PROFILES),
        default=["gpt55", "deepseek"],
    )
    parser.add_argument("--split", default="dev")
    parser.add_argument("--limit", type=int, default=234)
    parser.add_argument("--sleep-ms", type=int, default=1500)
    args = parser.parse_args()

    for name in args.profiles:
        profile = PROFILES[name]
        os.environ["AI_MODEL"] = profile["model"]
        argv = [
            "--split",
            args.split,
            "--limit",
            str(args.limit),
            "--sleep-ms",
            str(args.sleep_ms),
            "--output",
            profile["output"],
        ]
        print(f"Running profile={name} model={profile['model']}")
        code = run_golden_llm_eval_main(argv)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
