from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import nbformat

from scripts.build_research_notebook import (
    AI_ROOT,
    NOTEBOOK_PATH,
    PART_HEADERS,
    build_notebook,
    validate_notebook,
)


def _notebook_text(notebook: dict) -> str:
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


class ResearchNotebookContractTests(unittest.TestCase):
    def test_checked_in_notebook_matches_five_part_pipeline(self) -> None:
        if not NOTEBOOK_PATH.is_file():
            self.skipTest("Notebook not present; run build_notebook() in CI with full tree")
        notebook = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
        text = _notebook_text(notebook)
        positions = [text.index(part) for part in PART_HEADERS]
        self.assertEqual(sorted(positions), positions)
        self.assertEqual([], validate_notebook(notebook))

    def test_notebook_loads_shared_result_artifacts(self) -> None:
        text = _notebook_text(nbformat.read(str(NOTEBOOK_PATH), as_version=4))
        self.assertIn("notebook_live_test.json", text)
        self.assertIn("dual_model_test.json", text)
        self.assertIn("cx/gpt-5.6-luna-review", text)
        self.assertIn("http_429", text)
        self.assertIn("fallback", text.casefold())
        self.assertIn("Bảng thuật ngữ metric", text)
        self.assertIn("Bản đồ bằng chứng (staging)", text)
        self.assertIn("format_part12_narrative", text)
        self.assertIn("format_part13_narrative", text)
        self.assertIn("Hit@5: screening notebook vs release gate", text)
        self.assertIn("## 18. Đưa vào production — kết luận báo cáo", text)
        self.assertIn("Tính năng từ notebook", text)
        self.assertGreater(
            text.index("## 18. Đưa vào production — kết luận báo cáo"),
            text.index("## 17. Kết luận"),
        )
        self.assertIn("format_artifact_provenance_table", text)

    def test_notebook_has_no_fabricated_release_headline(self) -> None:
        text = _notebook_text(nbformat.read(str(NOTEBOOK_PATH), as_version=4))
        self.assertNotIn("composite_pass=100", text)
        self.assertNotIn("DeepSeek dẫn đầu 50%", text)
        self.assertNotIn("85% Hit@5", text)

    def test_notebook_keeps_code_visible(self) -> None:
        notebook = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            metadata = cell.get("metadata") or {}
            self.assertFalse(metadata.get("hide_input"))
            self.assertFalse(metadata.get("source_hidden"))

    def test_validator_accepts_nbformat_round_trip(self) -> None:
        notebook = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
        with tempfile.TemporaryDirectory(prefix="fable-notebook-roundtrip-") as temp_dir:
            path = Path(temp_dir) / "research.ipynb"
            nbformat.write(notebook, path)
            reloaded = nbformat.read(path, as_version=4)
        self.assertEqual([], validate_notebook(reloaded))

    def test_repository_keeps_exactly_one_notebook(self) -> None:
        notebooks = sorted(AI_ROOT.rglob("*.ipynb"))
        self.assertEqual([NOTEBOOK_PATH], notebooks)


if __name__ == "__main__":
    unittest.main()
