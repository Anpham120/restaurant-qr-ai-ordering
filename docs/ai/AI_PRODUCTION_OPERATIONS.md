# AI Production Operations — Pipeline v2

## Feature flag

- `CHAT_AI_PROVIDER=python-rag` (required on .NET backend)
- `AI_PIPELINE=v2` documents the LLM-first path (prompt lives only in Python)
- Python AI service LLM via **9router** (OpenAI-compatible):
  - `LLM_PROVIDER=9router`
  - `LLM_BASE_URL=http://localhost:20128/v1` (or deployed gateway URL)
  - `LLM_API_KEY=<9router gateway key>`
  - `LLM_MODEL=cx/gpt-5.6-luna-review` (production default; see
    `ai/app/config.py:DEFAULT_LLM_MODEL`)
  - Alternate quality gate: `LLM_MODEL=cx/gpt-5.5`
  - DeepSeek (`oc/deepseek-v4-flash-free`) is no longer the default — dropped
    after the 9router route serving it rejected `response_format:json_object`,
    which every real chat request requires. Historical research artifacts
    (`ai/evaluation/approved/pipeline_selection.json`) still reference it as the
    model tested at that time.
- `LLM_TIMEOUT_SECONDS=12` (Python-to-9router) and `BACKEND_AI_TIMEOUT_SECONDS=12` (.NET-to-Python)
- `AI_MAX_RETRY=0`–`1`

## Hard gates before canary

| Gate | Threshold |
|------|-----------|
| Menu ID validity | 100% |
| Unavailable suggestions | 0 |
| Duplicate auto-recommendations | 0 |
| Session history restore | 100% |
| Schema-valid responses | ≥ 99.5% |
| Fast-path catalog p95 | ≤ 100 ms |
| LLM TTFT p50 | ≤ 1.5 s |

## Rollout

1. Staging deploy with migration `AddsAiSessionLedgerAndServerCart`
2. Shadow evaluate Python responses offline for ≥ 1 week
3. Canary 10% tables via feature flag
4. Full production; keep rollback to previous image

## Rate limits

- 10 messages / minute / chat session
- 100 messages / chat session lifetime
- Max message length 2000 chars

## Observability

Log (no raw PII / message body):
- stage latency (retrieval, LLM, validate)
- validator rejection reason
- duplicate-blocked count
- fallback reason
- approximate token usage if provided by the LLM gateway

## Knowledge ownership

Restaurant manager owns KB domains with `expires_at`. Re-run `ai/scripts/build_index.py` after KB edits. Reject deploy if validation errors present.
