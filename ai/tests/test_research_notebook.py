"""Contract for the single research notebook the project ships.

The repository used to carry three notebooks — an early retrieval study, a
canonical report meant to replace it, and this system study — plus five build
scripts and two contract tests between them.  Readers had no way to tell which
one held the current numbers.  There is now exactly one notebook, and this file
pins the properties that make it trustworthy: the parts appear in order, the
numbers come from named artifacts, no retired configuration is presented as
current, and every code cell actually ran.

The notebook is checked against the committed file rather than by importing its
builder: `scripts/build_rag_llm_research.py` writes the notebook as a top-level
side effect, so importing it would regenerate a 147-cell notebook during the test
run and prove nothing about what is committed.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import nbformat

AI_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = AI_ROOT / "notebooks" / "rag_llm_system_research.ipynb"

PART_HEADERS = (
    "PHẦN I — BÀI TOÁN, TRI THỨC VÀ TẬP ĐÁNH GIÁ",
    "PHẦN II — THỰC NGHIỆM SO SÁNH CÁC PHƯƠNG PHÁP TRUY HỒI",
    "PHẦN III — TỪ TRUY HỒI ĐẾN TRỢ LÝ CÓ NGỮ CẢNH",
    "PHẦN IV — THỰC NGHIỆM TOÀN HỆ THỐNG",
    "PHẦN V — CHỐT PHƯƠNG ÁN PRODUCTION",
)

# Artifacts the notebook must read rather than restate from memory.  A number in
# the narrative with no artifact behind it is the failure mode this guards.
REQUIRED_ARTIFACTS = (
    "knowledge_manifest.json",
    "dev_retrieval_summary.v3.json",
    "retrieval_ablation_summary.json",
    "golden_chat_e2e.json",
    "session_e2e_eval.json",
    "intent_classification_eval_comparison.json",
    "pipeline_selection.json",
)

# Configuration that was retired.  Presenting any of it as the current setup is
# the mistake that made the older notebooks untrustworthy.
FORBIDDEN = (
    "composite_pass=100",
    "DeepSeek dẫn đầu 50%",
    "85% Hit@5",
)


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(str(NOTEBOOK_PATH), as_version=4)


def _text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


class ResearchNotebookContractTests(unittest.TestCase):
    def test_repository_ships_exactly_one_research_notebook(self) -> None:
        self.assertEqual([NOTEBOOK_PATH], sorted(AI_ROOT.rglob("*.ipynb")))

    def test_five_parts_appear_in_order(self) -> None:
        text = _text(_notebook())
        positions = [text.index(part) for part in PART_HEADERS]
        self.assertEqual(sorted(positions), positions)

    def test_every_number_is_read_from_a_named_artifact(self) -> None:
        text = _text(_notebook())
        for artifact in REQUIRED_ARTIFACTS:
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, text)

    def test_states_the_deployed_model_and_the_approved_winner(self) -> None:
        text = _text(_notebook())
        self.assertIn("cx/gpt-5.6-luna-review", text)
        self.assertIn("evidence_first_v2", text)

    def test_presents_no_retired_configuration_as_current(self) -> None:
        text = _text(_notebook())
        for phrase in FORBIDDEN:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)

    def test_keeps_code_visible(self) -> None:
        for cell in _notebook().cells:
            if cell.cell_type != "code":
                continue
            metadata = cell.get("metadata") or {}
            self.assertFalse(metadata.get("hide_input"))
            self.assertFalse(metadata.get("source_hidden"))

    def test_every_code_cell_ran_and_none_raised(self) -> None:
        # A notebook committed without outputs looks identical to one whose cells
        # all failed silently: both report zero error cells.  Assert both halves.
        code_cells = [c for c in _notebook().cells if c.cell_type == "code"]
        self.assertTrue(code_cells)
        without_output = [i for i, c in enumerate(code_cells) if not c.get("outputs")]
        self.assertEqual([], without_output)
        errored = [
            i
            for i, c in enumerate(code_cells)
            if any(o.get("output_type") == "error" for o in c.get("outputs") or [])
        ]
        self.assertEqual([], errored)

    def test_survives_an_nbformat_round_trip(self) -> None:
        notebook = _notebook()
        with tempfile.TemporaryDirectory(prefix="research-notebook-roundtrip-") as tmp:
            path = Path(tmp) / "research.ipynb"
            nbformat.write(notebook, path)
            reloaded = nbformat.read(path, as_version=4)
        self.assertEqual(len(notebook.cells), len(reloaded.cells))
        self.assertEqual(_text(notebook), _text(reloaded))


if __name__ == "__main__":
    unittest.main()
