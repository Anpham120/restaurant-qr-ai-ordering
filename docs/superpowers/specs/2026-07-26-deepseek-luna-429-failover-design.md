# DeepSeek-to-Luna 429 Failover Design

## Goal

Keep `oc/deepseek-v4-flash-free` as the primary production model while making
chat requests survive a DeepSeek rate-limit response by retrying that same
logical LLM operation once with `cx/gpt-5.6-luna-review`.

The research notebook remains the source of truth: it must evaluate the same
two-model policy that production runs, record which model actually answered,
and bind deployment to an approved result artifact.

## Approved policy

The user selected per-request failover (option B):

1. Every logical LLM operation starts with DeepSeek.
2. The first HTTP 429 from DeepSeek immediately triggers one Luna request with
   the same messages, schema, evidence boundary, token budget and temperature.
3. The next user request starts with DeepSeek again. There is no shared
   cooldown, circuit breaker or sticky Luna mode.
4. Timeout, connection failure, HTTP 5xx, malformed JSON, empty output and
   verifier rejection do not switch models.
5. A Luna failure does not start another fallback chain. Existing bounded,
   safe provider-unavailable behavior is used.

The policy applies independently to answer generation, semantic planning,
intent classification and streaming. A single chat request can therefore have
more than one model attempt, but each operation has at most:

```text
DeepSeek -> (only on HTTP 429) -> Luna
```

## Runtime architecture

### Configuration

Production configuration has explicit primary and fallback roles:

- `LLM_MODEL=oc/deepseek-v4-flash-free`
- `LLM_RATE_LIMIT_FALLBACK_MODEL=cx/gpt-5.6-luna-review`
- `LLM_RATE_LIMIT_FALLBACK_ENABLED=true`

Both models use the existing 9router base URL and API key. Startup validation
fails closed if the primary is not DeepSeek, the enabled fallback is not the
approved Luna identifier, or the two identifiers are equal. Tests and research
may disable fallback explicitly; production may not.

### Request execution

The router client builds payloads for a supplied model rather than relying on
one mutable model field. Model-specific structured-output behavior is rebuilt
for the fallback request:

- DeepSeek receives the existing JSON-object prompt adaptation and
  `reasoning_effort=none`.
- Luna receives the same semantic schema using its supported strict JSON-schema
  request format and configured reasoning effort.

HTTP 429 is represented by a typed rate-limit outcome, not detected from text.
The fallback request starts immediately and remains inside the existing request
budget. No global mutable "current model" is introduced, so concurrent sessions
cannot leak model state into one another.

### Result and telemetry contract

Each logical completion returns its text plus an immutable attempt trace. An
attempt contains:

- model identifier;
- role (`primary` or `rate_limit_fallback`);
- outcome (`success`, `http_429`, or bounded error category);
- HTTP status when available;
- latency.

The chat response preserves `model` as the model that generated the final
customer-visible answer and adds:

- `primary_model`;
- `fallback_model`;
- `fallback_used`;
- `fallback_reason`, equal to `rate_limit_429` when used;
- `model_attempts`.

Request logs include the same model route together with `pipeline_profile`,
decision route, resolved menu-item IDs and verifier result. API keys, prompts,
raw provider bodies and private state are never logged. Deterministic answers
continue to identify their deterministic model and do not claim Luna usage.

## Evidence and safety invariants

Failover changes availability, not authority. DeepSeek and Luna receive the same
menu evidence, KB chunks, session state and prompt constraints. Luna output
passes through the same parser, ID/price validation, claim verifier, allergy
rules, prompt-injection defenses and cart-confirmation rules.

The following remain hard failures:

- unsupported menu IDs or prices;
- a recommendation outside the allowed evidence set;
- allergy violations;
- AI-generated content persisted as fact;
- cross-session state leakage.

A provider response that fails these checks is rejected; it does not trigger
the other model.

## Research and notebook alignment

The notebook keeps the existing historical model comparison and the controlled
three-profile architecture comparison. It adds a clearly dated two-model
availability section:

1. direct DeepSeek probe;
2. direct Luna probe using the same representative quality/safety cases;
3. injected DeepSeek-429 failover tests proving the exact production route;
4. observed call counts, rate-limit rate, effective-model distribution,
   semantic success, safety result and latency.

The three pipeline profiles are then evaluated under the production policy
`DeepSeek primary -> Luna only on 429`. Every profile uses the same menu, KB,
dataset, budgets and policy. The artifact records both configured and effective
models per case, so a quota-limited run cannot be presented as a
DeepSeek-only experiment.

`pipeline_selection.json` is upgraded to include:

- primary and fallback model identifiers;
- trigger policy and maximum fallback count;
- per-model attempt/success/failure counts;
- fallback rate;
- all existing profile metrics, safety gates and provenance.

Winner selection remains safety -> semantic quality -> context accuracy ->
latency -> fewer provider calls. It does not prefer a profile merely because
one model happened to answer more often.

The generated notebook reads the artifact; it does not hardcode the winner or
invent missing comparison results. Historical results retain their original
model and timestamp labels.

## Deployment binding

Staging and production workflows verify all of the following before deployment:

- `AI_PIPELINE_PROFILE` equals the artifact winner;
- `LLM_MODEL` equals the artifact primary model;
- enabled fallback model and trigger equal the artifact policy;
- source/research hash and dataset hash are current;
- all safety gates passed.

CI and staging smoke check the normal DeepSeek path when available and use an
injected 9router transport that forces a primary 429 and proves the response was
generated by Luna. The injection exists only in the test/staging harness; no
public or production endpoint can select a model or force provider errors.
Production smoke verifies the bound model policy through internal health
metadata, then sends the real restaurant questions through the backend SSE
endpoint and rejects generic slow/provider-unavailable responses for the proven
cases.

Only the exact commit and model policy that pass staging may be promoted to
`main`. A mismatch between runtime health metadata, artifact policy, workflow
configuration or smoke output stops deployment or rolls it back.

## Test strategy

### Router unit tests

- DeepSeek success does not call Luna.
- DeepSeek 429 calls Luna exactly once with equivalent semantic input.
- DeepSeek timeout, connection error and each retryable 5xx do not call Luna.
- Luna 429, timeout, 5xx, empty output and malformed payload terminate safely.
- Structured and streaming requests rebuild the correct Luna payload.
- traces report exact attempt order, model, outcome and latency.
- parallel requests do not share traces or fallback state.

### Service and contract tests

- final-answer model and fallback metadata are correct.
- deterministic responses do not falsely report fallback.
- planner/classifier and answer attempts are observable.
- Luna output still passes evidence, ID, price, allergy and claim gates.
- fallback failure returns the existing safe provider-unavailable contract.
- no trace or state leaks between sessions.

### Evaluation, notebook and workflow tests

- real Luna representative quality/safety evaluation;
- injected 429 availability evaluation;
- three profiles evaluated under one identical policy;
- winner recomputation matches the artifact;
- notebook rebuild and validation succeed;
- deployment verifier rejects any model/policy/hash mismatch;
- staging backend SSE and forced-429 smoke both pass before production.

## Rollout

1. Implement tests first, then runtime and telemetry.
2. Generate the controlled artifact and notebook from the same commit.
3. Open a PR to `develop`; require all quality and research gates.
4. Deploy that commit to staging and run real-chat plus forced-429 smoke.
5. Promote the same commit and configuration to `main`.
6. Verify the supplied production table-session URL and inspect model-route,
   evidence and verifier telemetry.

Rollback restores the previous production image and disables the fallback
configuration together; production must never silently run a model policy that
is absent from its approved artifact.
