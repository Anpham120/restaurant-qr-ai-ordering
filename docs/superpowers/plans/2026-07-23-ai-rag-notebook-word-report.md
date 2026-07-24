# AI/RAG Academic Notebook and Word Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the single AI/RAG notebook as a sequential academic pipeline and generate an editable Word report matching the structure of `Nhom1_TTNT_FINAL.pdf`, without HTML output or unmeasured placeholder charts.

**Architecture:** Locked evaluation artifacts feed one shared academic data model. Matplotlib/Seaborn generate measured or explanatory figures, the notebook displays code and outputs, and a `python-docx` builder produces the code-free academic report. Notebook and Word therefore use the same metric helpers, figure manifest, captions and evidence limitations.

**Tech Stack:** Python 3.13, nbformat/nbclient, Matplotlib, Seaborn, Pandas, python-docx, unittest, Microsoft Word/LibreOffice rendering for visual QA.

## Global Constraints

- Keep exactly one `.ipynb`: `ai/notebooks/rag_retrieval_research.ipynb`.
- Do not generate or deliver HTML.
- Do not use Plotly or browser-rendered charts.
- Notebook shows Python code; Word contains no source code.
- Main narrative includes only `design`, `measured`, or explicitly sample-limited real measurements.
- `not_measured` figures never appear in the main notebook or Word report.
- All metrics come from locked artifacts and retain source, split and sample size.
- Final Word path is `output/reports/Bao_cao_do_an_AI_RAG_CMC_Restaurant.docx`.
- PDF may only be generated under `tmp/pdfs/` for visual QA.

---

### Task 1: Shared academic report data model

**Files:**
- Create: `ai/reporting/__init__.py`
- Create: `ai/reporting/academic_content.py`
- Create: `ai/tests/test_academic_content.py`

**Interfaces:**
- Consumes: `evaluation.report_visuals.preflight_report_artifacts`, locked JSON artifacts and `figure_manifest.json`.
- Produces:
  - `MAIN_FIGURE_IDS: tuple[str, ...]`
  - `FUTURE_EXPERIMENTS: tuple[dict[str, str], ...]`
  - `AcademicReportData`
  - `load_academic_report_data(run_id: str) -> AcademicReportData`
  - `rate_text(value: dict[str, object] | None) -> str`

- [ ] **Step 1: Write failing tests for figure filtering and metric denominators**

```python
def test_main_figure_policy_excludes_unmeasured_figures() -> None:
    data = load_academic_report_data("latest-approved")
    statuses = {item["figure_id"]: item["status"] for item in data.figures}
    assert all(statuses[item] != "not_measured" for item in MAIN_FIGURE_IDS)
    assert {"R03", "R04", "R12", "R16"}.isdisjoint(MAIN_FIGURE_IDS)


def test_rate_text_keeps_numerator_and_denominator() -> None:
    assert rate_text({"numerator": 11, "denominator": 18}) == "11/18 (61,11%)"
    assert rate_text(None) == "Chưa có phép đo"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_academic_content
```

Expected: import failure because `reporting.academic_content` does not exist.

- [ ] **Step 3: Implement the typed data model and locked loaders**

```python
@dataclass(frozen=True)
class AcademicReportData:
    preflight: dict[str, Any]
    knowledge: dict[str, Any]
    retrieval: dict[str, Any]
    retrieval_detail: dict[str, Any]
    release_candidate: dict[str, Any]
    sessions: dict[str, Any]
    dual: dict[str, Any]
    figures: tuple[dict[str, Any], ...]


MAIN_FIGURE_IDS = (
    "A01", "A02", "A03", "A04", "A05", "A06",
    "R01", "R02", "R05", "R06", "R07", "R08",
    "R10", "R11", "R13", "R14", "R15",
    "C01", "C02", "C03", "C04",
)
```

The loader must fail if a required artifact is absent, a lock hash differs, a main figure is absent, or a main figure has status `not_measured`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_academic_content
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add ai/reporting/__init__.py ai/reporting/academic_content.py ai/tests/test_academic_content.py
git commit -m "feat(ai-report): add locked academic content model"
```

---

### Task 2: Measured-only Python figure pipeline

**Files:**
- Modify: `ai/evaluation/report_visuals.py`
- Modify: `ai/tests/test_report_visuals.py`
- Modify: `ai/requirements-evaluation.txt`

**Interfaces:**
- Consumes: `MAIN_FIGURE_IDS` from the shared content model.
- Produces:
  - `generate_academic_report_assets(run_id: str) -> dict[str, Any]`
  - PNG figures at 300 DPI
  - Manifest entries only for generated academic figures

- [ ] **Step 1: Write failing tests for measured-only generation**

```python
def test_academic_assets_never_generate_placeholder_figures(self) -> None:
    manifest = generate_academic_report_assets("latest-approved")
    by_id = {item["figure_id"]: item for item in manifest["figures"]}
    self.assertEqual(set(MAIN_FIGURE_IDS), set(by_id))
    self.assertTrue(all(item["status"] != "not_measured" for item in by_id.values()))


def test_report_visuals_do_not_import_plotly(self) -> None:
    source = Path(report_visuals.__file__).read_text(encoding="utf-8").casefold()
    self.assertNotIn("plotly", source)
    self.assertNotIn("kaleido", source)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_report_visuals
```

Expected: missing `generate_academic_report_assets` and Plotly dependency remains.

- [ ] **Step 3: Implement strict figure selection**

Add a generator that invokes only the plotters backing `MAIN_FIGURE_IDS`.
If a selected plotter returns `not_measured`, raise:

```python
raise RuntimeError(
    f"Academic figure {figure_id} is not measured; move it to FUTURE_EXPERIMENTS"
)
```

Keep architecture diagrams in Matplotlib patches. Save PNG at 300 DPI and SVG
for reusable architecture assets. Remove Plotly from `requirements-evaluation.txt`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_report_visuals
```

Expected: all tests pass and academic manifest contains no placeholder.

- [ ] **Step 5: Commit**

```powershell
git add ai/evaluation/report_visuals.py ai/tests/test_report_visuals.py ai/requirements-evaluation.txt
git commit -m "feat(ai-report): generate measured Python figures only"
```

---

### Task 3: Rebuild the notebook as a sequential academic pipeline

**Files:**
- Modify: `ai/scripts/build_research_notebook.py`
- Modify: `ai/tests/test_research_notebook.py`

**Interfaces:**
- Consumes: `AcademicReportData`, `MAIN_FIGURE_IDS`, academic figure manifest.
- Produces:
  - `build_notebook(run_id: str) -> dict[str, Any]`
  - `validate_notebook(notebook) -> list[str]`
  - executed `ai/notebooks/rag_retrieval_research.ipynb`

- [ ] **Step 1: Replace old structural tests with pipeline acceptance tests**

```python
def test_notebook_uses_five_sequential_academic_parts(self) -> None:
    notebook = build_notebook()
    text = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
    expected = [
        "# PHẦN I — BÀI TOÁN VÀ DỮ LIỆU",
        "# PHẦN II — XÂY DỰNG HỆ THỐNG TRUY XUẤT RAG",
        "# PHẦN III — XÂY DỰNG CHATBOT CÓ NGỮ CẢNH",
        "# PHẦN IV — THỰC NGHIỆM VÀ KẾT QUẢ",
        "# PHẦN V — KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN",
    ]
    positions = [text.index(item) for item in expected]
    self.assertEqual(positions, sorted(positions))


def test_notebook_has_no_html_export_or_unmeasured_main_figures(self) -> None:
    source = inspect.getsource(notebook_builder)
    self.assertNotIn("export_html", source)
    self.assertNotIn("HTMLExporter", source)
    notebook_text = json.dumps(build_notebook(), ensure_ascii=False)
    for figure_id in ("R03", "R04", "R12", "R16"):
        self.assertNotIn(f'show_figures("{figure_id}")', notebook_text)
```

Also assert that every result section contains the words `Nhận xét` and
`Quyết định`, and that the notebook source contains no repeated generic
`Mục tiêu của chương` template.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_research_notebook
```

Expected: current 15-chapter notebook and HTML exporters violate the contract.

- [ ] **Step 3: Rewrite notebook construction**

Build approximately 80-110 cells, following the reference notebook rhythm:

```python
cells.extend([
    md("# PHẦN II — XÂY DỰNG HỆ THỐNG TRUY XUẤT RAG"),
    md("## II.1 BM25 — truy xuất theo từ khóa\n\n..."
       "### Vấn đề cần giải quyết\n..."
       "### Nguyên lý\n..."),
    code("from app.rag.retriever import BM25Retriever\n..."),
    md("### Ví dụ kết quả BM25"),
    code("display_retrieval_example('bm25', example_query)"),
    md("**Nhận xét.** ...\n\n**Quyết định.** ..."),
])
```

Place metric explanations before retrieval/LLM result cells. Present one
12-turn session throughout Part III. Show source excerpts only in notebook
outputs. Remove `chapter()`, `export_html()`, `export_pdf()` and HTML-related
CLI flags.

- [ ] **Step 4: Execute and validate the notebook**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_research_notebook.py --execute
```

Expected: notebook executes with zero cell errors and produces all main figures.

- [ ] **Step 5: Run notebook tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_research_notebook
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add ai/scripts/build_research_notebook.py ai/notebooks/rag_retrieval_research.ipynb ai/tests/test_research_notebook.py
git commit -m "feat(ai-report): rebuild RAG notebook as academic pipeline"
```

---

### Task 4: Generate the editable academic Word report

**Files:**
- Create: `ai/reporting/word_report.py`
- Create: `ai/scripts/build_academic_report.py`
- Create: `ai/tests/test_academic_word_report.py`
- Modify: `ai/requirements-evaluation.txt`

**Interfaces:**
- Consumes: `AcademicReportData`, academic figure manifest and PNG assets.
- Produces:
  - `build_academic_report(data: AcademicReportData, output_path: Path) -> Path`
  - `validate_academic_report(path: Path) -> list[str]`
  - `output/reports/Bao_cao_do_an_AI_RAG_CMC_Restaurant.docx`

- [ ] **Step 1: Write failing Word structure tests**

```python
def test_word_report_has_required_academic_sections(self) -> None:
    path = build_test_report()
    document = Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    for heading in (
        "TÓM TẮT",
        "CHƯƠNG 1: GIỚI THIỆU",
        "CHƯƠNG 2: CƠ SỞ LÝ THUYẾT",
        "CHƯƠNG 3: PHƯƠNG PHÁP THỰC NGHIỆM",
        "CHƯƠNG 4: THỰC NGHIỆM VÀ KẾT QUẢ",
        "CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN",
        "TÀI LIỆU THAM KHẢO",
        "PHỤ LỤC",
    ):
        self.assertIn(heading, text)


def test_word_report_contains_no_source_code_or_unmeasured_figures(self) -> None:
    path = build_test_report()
    document = Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    self.assertNotIn("def ", text)
    self.assertNotIn("from app.", text)
    for figure_id in ("R03", "R04", "R12", "R16"):
        self.assertNotIn(figure_id, text)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_academic_word_report
```

Expected: module `reporting.word_report` does not exist.

- [ ] **Step 3: Add `python-docx` dependency and Word builder**

Add:

```text
python-docx>=1.1,<2.0
```

The builder must configure:

```python
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.top_margin = Cm(2)
section.bottom_margin = Cm(2)
section.left_margin = Cm(3)
section.right_margin = Cm(2)
normal.font.name = "Times New Roman"
normal.font.size = Pt(13)
normal.paragraph_format.line_spacing = 1.5
```

Add Word fields for TOC, list of figures and list of tables. Use numbered heading
styles, blue table headers, centered captions and page-number footer. Build all
five chapters from measured data and insert PNG figures at report width.

- [ ] **Step 4: Add semantic report validation**

Validation must check:

- required headings;
- at least 15 embedded figures;
- at least 10 tables;
- zero forbidden source-code markers;
- zero main references to `not_measured`;
- every `Hình N.M` caption followed by a Vietnamese analysis paragraph;
- all main figure IDs occur exactly once.

- [ ] **Step 5: Run Word tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_academic_word_report
```

Expected: all tests pass.

- [ ] **Step 6: Build final Word artifact**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\build_academic_report.py --run-id latest-approved
```

Expected:

```text
Word report: .../output/reports/Bao_cao_do_an_AI_RAG_CMC_Restaurant.docx
Validation: PASS
```

- [ ] **Step 7: Commit**

```powershell
git add ai/reporting/word_report.py ai/scripts/build_academic_report.py ai/tests/test_academic_word_report.py ai/requirements-evaluation.txt
git commit -m "feat(ai-report): generate editable academic Word report"
```

---

### Task 5: Remove HTML deliverables and stale report paths

**Files:**
- Modify: `ai/tests/test_research_notebook.py`
- Modify: `ai/evaluation/README.md`
- Modify: `docs/ai/AI_EVALUATION_REPORT.md`
- Delete generated current HTML: `ai/evaluation/results/report/latest-approved/rag_retrieval_research.html`
- Delete generated old PDF: `output/pdf/rag_retrieval_research.pdf`

**Interfaces:**
- Consumes: final notebook and Word report paths.
- Produces: documentation that names only notebook, Word and PNG figures as deliverables.

- [ ] **Step 1: Add a repository-level no-HTML contract test**

```python
def test_current_report_outputs_contain_no_html(self) -> None:
    html_files = list((AI_ROOT / "evaluation" / "results" / "report").rglob("*.html"))
    self.assertEqual([], html_files)
```

- [ ] **Step 2: Run test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_research_notebook
```

Expected: current HTML file is reported.

- [ ] **Step 3: Remove stale outputs and update documentation**

Use exact-path removal only after validating both paths are inside the repository.
Update commands to:

```powershell
python scripts/build_research_notebook.py --execute
python scripts/build_academic_report.py --run-id latest-approved
```

- [ ] **Step 4: Run test and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_research_notebook
```

Expected: no HTML output remains.

- [ ] **Step 5: Commit**

```powershell
git add ai/tests/test_research_notebook.py ai/evaluation/README.md docs/ai/AI_EVALUATION_REPORT.md
git commit -m "docs(ai-report): make notebook and Word the only report outputs"
```

---

### Task 6: Visual QA of notebook and Word

**Files:**
- Verify: `ai/notebooks/rag_retrieval_research.ipynb`
- Verify: `output/reports/Bao_cao_do_an_AI_RAG_CMC_Restaurant.docx`
- Temporary: `tmp/pdfs/academic-ai-rag-report/`

**Interfaces:**
- Consumes: executed notebook and final Word report.
- Produces: visual inspection evidence; no additional deliverable format.

- [ ] **Step 1: Inspect notebook outputs**

Programmatically assert:

```python
assert all(
    output.get("output_type") != "error"
    for cell in notebook["cells"]
    for output in cell.get("outputs", [])
)
```

Render representative notebook figures and inspect Part I through Part V.

- [ ] **Step 2: Render Word to temporary PDF**

Use Microsoft Word COM or LibreOffice to export under:

```text
tmp/pdfs/academic-ai-rag-report/Bao_cao_do_an_AI_RAG_CMC_Restaurant.pdf
```

Do not place this PDF in final output.

- [ ] **Step 3: Render PDF pages to PNG and inspect**

Inspect:

- cover;
- abstract;
- TOC/list pages;
- first page of every chapter;
- representative architecture, retrieval, session and LLM result pages;
- conclusion, references and appendix.

Reject output if there is clipped text, overlapping figures, split captions,
or tables outside margins.

- [ ] **Step 4: Remove temporary render files**

After QA passes, delete only:

```text
tmp/pdfs/academic-ai-rag-report/
```

The Word report and PNG figures remain.

---

### Task 7: Full verification and completion audit

**Files:**
- Verify all modified files and final artifacts.

**Interfaces:**
- Consumes: all tasks.
- Produces: completion evidence.

- [ ] **Step 1: Run focused report tests**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_academic_content `
  tests.test_report_visuals `
  tests.test_research_notebook `
  tests.test_academic_word_report
```

Expected: zero failures.

- [ ] **Step 2: Run the full Python suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expected: zero failures.

- [ ] **Step 3: Verify deliverable contract**

Check:

- exactly one `.ipynb`;
- zero report `.html`;
- final `.docx` exists and passes semantic validation;
- all notebook cells executed without error;
- main figure manifest has no `not_measured`;
- Word and notebook metric values match locked artifacts.

- [ ] **Step 4: Review diff**

```powershell
git diff --check
git status --short
```

Preserve unrelated user changes and report remaining release limitations
without claiming production readiness.

