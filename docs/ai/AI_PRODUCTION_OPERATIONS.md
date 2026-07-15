# AI Production Operations — Pipeline v2

## Feature flag

- `AI_PROVIDER=python-rag` (required)
- `AI_PIPELINE=v2` documents the LLM-first path (prompt lives only in Python)
- `AI_TIMEOUT_SECONDS=15` (lowered from 60)
- `AI_MAX_RETRY=1`
- `AI_MODEL=gemini-3.5-flash`
- Optional fallback: `AI_FALLBACK_MODEL=gemini-2.0-flash-lite`

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
- approximate token usage if provided by Gemini

## Knowledge ownership

Restaurant manager owns KB domains with `expires_at`. Re-run `ai/scripts/build_index.py` after KB edits. Reject deploy if validation errors present.
