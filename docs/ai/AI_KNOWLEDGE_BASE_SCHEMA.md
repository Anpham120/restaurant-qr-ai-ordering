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
