"""Probe routing on paraphrases (not copied from eval catalog)."""

from __future__ import annotations

import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from evaluation.intent_eval_common import keyword_route

HIST4 = [
    {"role": "user", "content": "4 nguoi an gi"},
    {"role": "assistant", "content": "Goi y lau va goi."},
]
HIST5 = [
    {"role": "user", "content": "500k cho 5 nguoi"},
    {"role": "assistant", "content": "Combo khoang 480k."},
]

PROBES: list[dict] = [
    {"id": "ingredient_x_co", "message": "tom cua co khong", "history": HIST4, "wants": True, "party": 4},
    {"id": "ingredient_co_x", "message": "co hai san khong", "history": HIST4, "wants": True, "party": 4},
    {"id": "ingredient_co_tom", "message": "co tom khong", "history": HIST4, "wants": True, "party": 4},
    {"id": "ingredient_prior_dish", "message": "mon do co lac khong", "history": HIST4, "wants": True, "party": 4},
    {"id": "budget_du_tien", "message": "du tien khong", "history": HIST5, "wants": True, "party": 5},
    {"id": "budget_het_tien", "message": "het tien khong du", "history": HIST5, "wants": True, "party": 5},
    {"id": "party_nen_an", "message": "6 nguoi nen an gi", "history": [], "wants": True, "party": 6},
    {"id": "seating_control", "message": "wifi co khong", "history": [], "wants": False, "party": None},
]


def main() -> int:
    failures = 0
    for probe in PROBES:
        pred = keyword_route(probe["message"], probe["history"])
        ok_wants = pred["wants_recommendations"] == probe["wants"]
        ok_party = pred["party_size"] == probe["party"]
        passed = ok_wants and ok_party
        if not passed:
            failures += 1
        status = "PASS" if passed else "FAIL"
        print(f"{status} {probe['id']}: {probe['message']} -> {pred}")

    print(f"\nFailures: {failures}/{len(PROBES)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
