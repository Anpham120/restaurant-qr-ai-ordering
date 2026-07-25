# -*- coding: utf-8 -*-
"""Orchestrate building the five-part research notebook from part scripts."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import nbformat

AI_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_PATH = AI_ROOT / "notebooks" / "rag_retrieval_research.ipynb"

PART_SCRIPTS = (
    AI_ROOT / "scripts" / "build_part1.py",
    AI_ROOT / "scripts" / "build_part2.py",
    AI_ROOT / "scripts" / "build_part3_4_5.py",
)

PART_HEADERS = (
    "# PHẦN I — BÀI TOÁN VÀ DỮ LIỆU",
    "# PHẦN II — SO SÁNH CÁC PHƯƠNG PHÁP RETRIEVAL",
    "# PHẦN III — CHATBOT CÓ NGỮ CẢNH",
    "# PHẦN IV — THỰC NGHIỆM",
    "# PHẦN V — KẾT LUẬN",
)

FORBIDDEN_SOURCE_STRINGS = (
    "composite_pass=100",
    "DeepSeek dẫn đầu 50%",
    "85% Hit@5",
)

REQUIRED_MARKERS = (
    "Bảng thuật ngữ metric",
    "dual_model_test.json",
    "notebook_live_test.json",
    "notebook_retrieval_screening.json",
    "Bản đồ bằng chứng (staging)",
    "format_part4_narrative",
    "format_part12_narrative",
    "format_part13_narrative",
    "format_artifact_provenance_table",
    "Hit@5: screening notebook vs release gate",
    "## 18. Đưa vào production — kết luận báo cáo",
    "Tính năng từ notebook",
    "AI_STAGING_READINESS.md",
)

LIVE_SCRIPTS = (
    AI_ROOT / "scripts" / "_run_live_tests.py",
    AI_ROOT / "scripts" / "_dual_model_test.py",
)


def _notebook_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join("".join(cell.source) for cell in notebook.cells)


def build_notebook(run_id: str | None = None) -> nbformat.NotebookNode:
    del run_id  # reserved for future pinned artifact runs
    for script in PART_SCRIPTS:
        if not script.is_file():
            raise FileNotFoundError(f"Missing notebook builder: {script}")
        subprocess.run(
            [sys.executable, str(script)],
            cwd=str(AI_ROOT),
            check=True,
        )
    return nbformat.read(str(NOTEBOOK_PATH), as_version=4)


def validate_notebook(notebook: nbformat.NotebookNode) -> list[str]:
    errors: list[str] = []
    text = _notebook_text(notebook)

    for header in PART_HEADERS:
        if header not in text:
            errors.append(f"Missing section header: {header}")

    positions = [text.index(h) for h in PART_HEADERS if h in text]
    if positions != sorted(positions):
        errors.append("Part headers are out of order")

    for marker in REQUIRED_MARKERS:
        if marker not in text:
            errors.append(f"Missing required marker: {marker}")

    for forbidden in FORBIDDEN_SOURCE_STRINGS:
        if forbidden in text:
            errors.append(f"Forbidden static claim in notebook: {forbidden}")

    lock_marker = "## 18. Đưa vào production — kết luận báo cáo"
    sec17 = "## 17. Kết luận"
    if lock_marker in text and sec17 in text:
        if text.index(lock_marker) < text.index(sec17):
            errors.append("Production report section must appear after §17 Kết luận")

    code_cells = [c for c in notebook.cells if c.cell_type == "code"]
    if not code_cells:
        errors.append("Notebook has no code cells")

    for cell in code_cells:
        metadata = cell.get("metadata") or {}
        if metadata.get("hide_input") or metadata.get("source_hidden"):
            errors.append("Code cell has hidden input")
        if "hide-input" in (metadata.get("tags") or []):
            errors.append("Code cell tagged hide-input")

    return errors


def regen_live_artifacts() -> None:
    for script in LIVE_SCRIPTS:
        if not script.is_file():
            raise FileNotFoundError(f"Missing live export script: {script}")
        subprocess.run([sys.executable, str(script)], cwd=str(AI_ROOT), check=True)


def execute_notebook(timeout_seconds: int = 600) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--inplace",
            "--execute",
            str(NOTEBOOK_PATH),
            f"--ExecutePreprocessor.timeout={timeout_seconds}",
        ],
        cwd=str(AI_ROOT),
        check=True,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and validate research notebook")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate checked-in notebook without rebuilding",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run jupyter nbconvert --execute after build",
    )
    parser.add_argument(
        "--regen-live",
        action="store_true",
        help="Run _run_live_tests.py and _dual_model_test.py (requires 9router)",
    )
    parser.add_argument(
        "--regen-screening",
        action="store_true",
        help="Alias hint: screening JSON is written when Part II cells execute (--execute)",
    )
    parser.add_argument(
        "--execute-timeout",
        type=int,
        default=600,
        help="nbconvert ExecutePreprocessor timeout seconds",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.regen_screening and not args.execute:
        print("Note: --regen-screening requires --execute to run Part II export cell.")

    if args.validate_only:
        if not NOTEBOOK_PATH.is_file():
            print(f"Notebook not found: {NOTEBOOK_PATH}")
            return 1
        notebook = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
    else:
        notebook = build_notebook()

    issues = validate_notebook(notebook)
    if issues:
        for issue in issues:
            print(f"VALIDATION: {issue}")
        return 1

    if args.regen_live:
        regen_live_artifacts()

    if args.execute:
        execute_notebook(timeout_seconds=args.execute_timeout)
        notebook = nbformat.read(str(NOTEBOOK_PATH), as_version=4)
        issues = validate_notebook(notebook)
        if issues:
            for issue in issues:
                print(f"VALIDATION: {issue}")
            return 1

    print(f"OK {NOTEBOOK_PATH} ({len(notebook.cells)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
