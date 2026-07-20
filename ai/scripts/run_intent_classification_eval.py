"""Re-run intent classification eval (keyword vs hybrid, multi-model). Thin wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ROOT))

from evaluation.run_intent_classification_eval import main  # noqa: E402

if __name__ == "__main__":
    main()
