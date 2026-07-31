> ## ⚠️ TÀI LIỆU LỊCH SỬ — mô tả hệ thống AI **ĐÃ ĐƯỢC THAY**
>
> Tài liệu này nói về kiến trúc AI **trước khi** phần `ai/` được dựng lại từ số không. Những tệp nó
> nhắc tới — `ai/knowledge-base/`, `ai/app/services/assistant.py`, `ai/app/rag/kb_info_fast_path.py`,
> `ai/evaluation/golden/`, các "pipeline profile" — **không còn tồn tại trong repo**.
>
> **Hệ thống hiện tại:** xem `docs/ai/BAO_CAO_DO_AN_HOC_MAY_KPDL.md` (báo cáo đồ án, được SINH từ mã và
> bằng chứng đo), `ai/README.md` (bảy bước dựng lại) và `ai/notebooks/he_thong_ai_tu_van_dat_mon.ipynb`.
>
> Giữ lại thay vì xóa, vì nó ghi **điều kiện nào làm mỗi quyết định cũ đúng** — và dự án đã hai lần
> phải đảo lại một quyết định nhờ đọc đúng phần đó.

---

# Knowledge base chunk schema (audit reference)

Each markdown file under `ai/knowledge-base/` is split into chunks with:

- `source` — filename (e.g. `faq.md`)
- `title` — heading section
- `content` — body text
- `tags` — optional metadata tags

Run chunk audit after KB edits:

```powershell
PYTHONPATH=ai python ai/evaluation/audit_kb_chunks.py
```

Regenerate golden cases when chunk boundaries change:

```powershell
cd ai
py evaluation/generate_golden_cases.py
```

Target: keep chunks ≤ ~1200 chars; review `kb_chunk_audit.json` oversized samples.
