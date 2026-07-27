"""Structural checks for the new report notebook.

These checks intentionally inspect content rather than notebook execution so a
reviewer cannot accidentally publish a short or disconnected report.
"""

from __future__ import annotations

from pathlib import Path

import nbformat

from scripts.build_canonical_research_notebook import build_notebook


AI_ROOT = Path(__file__).resolve().parents[1]


def test_new_notebook_is_a_deep_five_part_report(tmp_path: Path) -> None:
    output = tmp_path / "restaurant_ai_research_report.ipynb"
    build_notebook(output)
    notebook = nbformat.read(output, as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells)

    assert len(notebook.cells) >= 110
    assert sum(cell.cell_type == "markdown" for cell in notebook.cells) >= 60
    for marker in (
            "PHẦN I — BÀI TOÁN VÀ DỮ LIỆU",
            "PHẦN II — SO SÁNH RETRIEVAL",
            "PHẦN III — CHATBOT CÓ NGỮ CẢNH",
            "PHẦN IV — THỰC NGHIỆM VÀ LỰA CHỌN",
        "PHẦN V — PRODUCTION",
        "Nhận xét",
        "pipeline_selection.json",
        "canonical-research-v1",
        "cx/gpt-5.6-luna-review",
        "## 1. Bài toán",
        "## 2. Khám phá Knowledge Base",
        "## 3. Chuẩn hóa tiếng Việt",
        "## 4. Tập đánh giá retrieval",
        "## 5. Ba phương pháp retrieval",
        "## 6. Đánh giá retrieval",
        "## 7. Kết luận retrieval",
        "## 8. Evidence routing",
        "## 9. Guardrails",
        "## 10. Session memory",
        "## 11. Claim verifier",
        "## 12. Ba pipeline",
        "## 13. Giao thức",
        "## 14. Kết quả",
        "## 15. So sánh model",
        "## 16. Pipeline selection",
        "## 17. Notebook → production",
        "## 18. Staging, rollback và kết luận",
        "Notebook cũ ↔ runtime hiện tại",
        "Đang chạy trong runtime",
        "Historical research",
        "Cần chạy lại",
        "Historical research — không phải release metric",
        "2.1 Phân bố chunk",
        "2.3 Question variants",
        "3.1 Demo chuẩn hóa",
        "6.2 False Positive",
        "6.4 Error analysis",
        "6.8 Tổng hợp — Heatmap",
        "Trace ba câu regression",
        "Guardrail → invariant → case",
        "State transition",
        "Claim → evidence",
        "CI fail-closed",
    ):
        assert marker in source
    assert source.count("#### Nhận xét") >= 18


def test_new_notebook_preserves_one_catalogue_and_legacy_reference(tmp_path: Path) -> None:
    # Never use the checked-in report as a test target: that would erase the
    # executed output that readers are meant to inspect.
    output = tmp_path / "restaurant_ai_research_report.ipynb"
    build_notebook(output)
    notebook = nbformat.read(output, as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells)

    assert "bundle.view(" in source
    assert "rag_retrieval_research.ipynb" in source
    assert "Ã" not in source
