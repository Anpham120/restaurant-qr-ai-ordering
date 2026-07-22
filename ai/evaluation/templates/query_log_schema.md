# Online query log schema (anonymous research backlog)

Store one JSON line per turn (no raw PII):

```json
{
  "ts": "2026-07-21T10:00:00Z",
  "session_id_hash": "sha256-prefix",
  "query_hash": "sha256-prefix",
  "intent": "payment",
  "path": "llm|fast_path|fallback",
  "retrieval_confidence": 0.72,
  "llm_model": "cx/gpt-5.5",
  "validator_pass": true,
  "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"]
}
```

Use aggregated logs to propose new golden families — do not replace golden set automatically.
