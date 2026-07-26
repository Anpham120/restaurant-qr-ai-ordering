# Chat Contract Production Fix Design

## Goal

Restore the real ordering-chat path on production and prevent deployment from passing when the browser-facing backend-to-Python integration is broken.

## Confirmed failure

The production backend serializes a new chat session with
`session_state.conversation_frame = null`. The Python `ChatRequest` contract
requires `conversation_frame` to be an object, so FastAPI rejects the request
before DeepSeek is called. The backend maps that upstream 4xx response to the
generic Vietnamese message saying the system is slow.

The deployment smoke test did not catch this because it called Python directly
with a hand-built, valid conversation-frame object instead of exercising the
same backend endpoint used by the ordering UI.

## Design

### Contract ownership

The backend is the producer of the V2 request and must always serialize a
complete typed state. When persisted state has no conversation frame, it will
send a default frame with empty lists, no active topic/intent/category, turn
sequence zero, no pending clarification, and empty constraint provenance.
Python keeps its strict non-null schema so future producer regressions remain
visible.

### Error observability

For non-success responses from Python, the backend will log the upstream status
code and a bounded response-body excerpt. Customer responses remain safe and do
not expose internal validation details. Contract failures receive a distinct
guardrail flag so logs and integration tests can distinguish them from provider
timeouts.

### Timeout alignment

The backend timeout must be greater than the Python request budget. Production
will use an 18-second backend timeout while Python retains its 14-second request
budget and 12-second DeepSeek timeout. This lets Python produce its own bounded
fallback instead of having the backend cancel first.

### Deployment gate

The existing direct-Python smoke remains responsible for verifying model,
profile, evidence, and verifier fields. A second smoke will create a chat
session through the public backend API, send a message through the SSE endpoint
used by the UI, and fail deployment if the final event contains
`AI_PROVIDER_UNAVAILABLE`, a contract-error flag, no assistant message, or the
generic slow fallback.

## Testing

- Backend regression test captures the real serialized V2 payload and asserts
  `conversation_frame` is an object for a new session.
- Backend regression test asserts upstream 4xx responses are classified and
  logged without exposing their body to the customer.
- Compose validation asserts the backend timeout default is 18 seconds.
- Deployment-script validation asserts a backend-path smoke exists in addition
  to the direct-Python semantic probes.
- Full backend, AI, frontend, compose, notebook, and workflow validations run
  before rollout.
- Staging and production are verified through the real public chat endpoint,
  followed by the exact production phrase `ở đây có phở không`.

## Scope

This fix does not change the three research profiles, DeepSeek model, winner
selection, retrieval method, evidence rules, or notebook conclusions.

