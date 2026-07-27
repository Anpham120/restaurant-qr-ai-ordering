# DeepSeek-to-Luna 429 Failover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every production LLM operation try DeepSeek first and retry once with GPT-5.6 Luna only after an HTTP 429, while keeping notebook research, approved artifacts, CI and deployed telemetry aligned with that exact policy.

**Architecture:** The 9router client owns per-operation fallback and writes immutable attempt records into a request-scoped `ContextVar` collector, so existing planner/classifier call sites inherit tracing without global cross-session state. The assistant snapshots that trace into the final response, and the profile evaluator aggregates the same response contract into the approved selection artifact and generated notebook. Deployment verifies the winner plus both model roles before starting containers.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, httpx, pytest/pytest-asyncio, Jupyter nbformat, Docker Compose, GitHub Actions, Bash/PowerShell, .NET 8 backend SSE gateway.

## Global Constraints

- Primary model is exactly `oc/deepseek-v4-flash-free`.
- Rate-limit fallback model is exactly `cx/gpt-5.6-luna-review`.
- Fallback is per logical LLM operation and only on a typed HTTP 429.
- The next logical operation always starts with DeepSeek; no cooldown, circuit breaker or sticky Luna state.
- Timeout, connection failure, HTTP 5xx, malformed JSON, empty output and verifier rejection never trigger Luna.
- A Luna failure terminates the provider path; no third attempt or fallback chain.
- DeepSeek and Luna share the same 9router base URL, API key, evidence, prompt semantics, safety gates and request budget.
- `model` remains the effective final-answer model; deterministic responses must not claim Luna usage.
- Production cannot enable a model policy absent from the approved research artifact.
- No test hook allowing model selection or forced provider errors is exposed by the production API.
- Preserve untracked user files `ai/_list_sections.py`, `ai/evaluation/results/pipeline_selection.json`, `docs/assets/ai-architecture/`, `scripts/prod-smoke-order-api.mjs`, and `scripts/prod-smoke-order-cart.mjs`.

---

## File map

- `ai/app/clients/router.py`: payload generation, typed 429 handling, one-shot Luna retry and request-scoped attempt capture.
- `ai/app/config.py`: exact primary/fallback settings and startup validation.
- `ai/app/schemas.py`: public/internal model-route response schema.
- `ai/app/services/assistant.py`: attach request trace to normal, streaming, deterministic and timeout responses.
- `ai/app/main.py`: health/readiness model-policy metadata and timeout contract.
- `ai/tests/test_router_client.py`: transport-level fallback and concurrency behavior.
- `ai/tests/test_router_config.py`: environment and model-role validation.
- `ai/tests/test_provider_observability.py`: response/log trace semantics.
- `ai/tests/test_chat_contract_v2.py`: response contract and timeout metadata.
- `ai/tests/test_pipeline_profile_eval.py`: per-model aggregation.
- `ai/tests/test_pipeline_selection.py`: winner behavior remains safety-first.
- `ai/tests/test_verify_pipeline_selection.py`: artifact/model-policy deployment binding.
- `ai/evaluation/run_pipeline_profile_eval.py`: controlled mixed-policy run and attempt metrics.
- `ai/evaluation/pipeline_selection.py`: artifact policy validation and selection explanation.
- `ai/evaluation/verify_pipeline_selection.py`: fail-closed deploy verifier.
- `ai/evaluation/research_inputs.py`: provenance coverage for fallback runtime and policy.
- `ai/evaluation/approved/pipeline_selection.json`: reviewed winner and model-policy evidence.
- `ai/evaluation/approved/README.md`: artifact promotion procedure.
- `ai/scripts/build_research_notebook.py`: generated two-model availability and production-policy sections.
- `ai/notebooks/rag_retrieval_research.ipynb`: generated report artifact.
- `ai/tests/test_notebook_pipeline_selection.py`: notebook-to-artifact assertions.
- `deploy/docker-compose.yml`: runtime model-role configuration.
- `deploy/env/staging.example.env`, `deploy/env/production.example.env`, `ai/.env.example`: operator-visible settings.
- `.github/workflows/research-pipeline-selection.yml`: controlled evaluation and raw artifact upload.
- `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-production.yml`: policy verification and exact configuration rollout.
- `deploy/scripts/deploy-vps.sh`: writes the verified model policy to the VPS environment.
- `deploy/scripts/health-check.sh`: normal public SSE/health policy smoke on the VPS.

---

### Task 1: Add exact model-role configuration

**Files:**
- Modify: `ai/app/config.py`
- Modify: `ai/tests/test_router_config.py`
- Modify: `ai/tests/test_ai_service_config_v2.py`
- Modify: `ai/.env.example`
- Modify: `deploy/env/staging.example.env`
- Modify: `deploy/env/production.example.env`

**Interfaces:**
- Produces: `DEFAULT_RATE_LIMIT_FALLBACK_MODEL: str`
- Produces: `AiServiceConfig.rate_limit_fallback_model: str`
- Produces: `AiServiceConfig.rate_limit_fallback_enabled: bool`
- Produces: `AiServiceConfig.model_policy_valid: bool`
- Consumes: existing `_canonical_env`, `_env_flag` and `is_supported_router_model`

- [ ] **Step 1: Write failing configuration tests**

Add tests that construct environment settings and assert these exact values:

```python
def test_load_config_enables_exact_luna_429_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_MODEL", "oc/deepseek-v4-flash-free")
    monkeypatch.setenv("LLM_RATE_LIMIT_FALLBACK_MODEL", "cx/gpt-5.6-luna-review")
    monkeypatch.setenv("LLM_RATE_LIMIT_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("RAG_KNOWLEDGE_BASE_PATH", str(tmp_path))
    config = load_config()
    assert config.model == "oc/deepseek-v4-flash-free"
    assert config.rate_limit_fallback_model == "cx/gpt-5.6-luna-review"
    assert config.rate_limit_fallback_enabled is True
    assert config.model_policy_valid is True


@pytest.mark.parametrize(
    ("primary", "fallback"),
    [
        ("cx/gpt-5.6-luna-review", "oc/deepseek-v4-flash-free"),
        ("oc/deepseek-v4-flash-free", "cx/gpt-5.5"),
        ("oc/deepseek-v4-flash-free", "oc/deepseek-v4-flash-free"),
    ],
)
def test_enabled_fallback_rejects_unapproved_model_roles(monkeypatch, primary, fallback):
    monkeypatch.setenv("LLM_MODEL", primary)
    monkeypatch.setenv("LLM_RATE_LIMIT_FALLBACK_MODEL", fallback)
    monkeypatch.setenv("LLM_RATE_LIMIT_FALLBACK_ENABLED", "true")
    with pytest.raises(ValueError, match="DeepSeek primary.*Luna fallback"):
        load_config()
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_router_config.py tests/test_ai_service_config_v2.py -q
```

Expected: failures because the fallback fields and Luna model support do not exist.

- [ ] **Step 3: Implement strict configuration**

Add the exact constants and fields:

```python
DEFAULT_LLM_MODEL = "oc/deepseek-v4-flash-free"
DEFAULT_RATE_LIMIT_FALLBACK_MODEL = "cx/gpt-5.6-luna-review"


@dataclass(frozen=True)
class AiServiceConfig:
    # existing fields remain in their current order
    rate_limit_fallback_model: str = DEFAULT_RATE_LIMIT_FALLBACK_MODEL
    rate_limit_fallback_enabled: bool = True

    @property
    def model_policy_valid(self) -> bool:
        if not self.rate_limit_fallback_enabled:
            return self.model == DEFAULT_LLM_MODEL
        return (
            self.model == DEFAULT_LLM_MODEL
            and self.rate_limit_fallback_model == DEFAULT_RATE_LIMIT_FALLBACK_MODEL
            and self.model != self.rate_limit_fallback_model
        )
```

In `load_config()`, read `LLM_RATE_LIMIT_FALLBACK_MODEL` and
`LLM_RATE_LIMIT_FALLBACK_ENABLED`, then raise:

```python
if rate_limit_fallback_enabled and (
    model != DEFAULT_LLM_MODEL
    or rate_limit_fallback_model != DEFAULT_RATE_LIMIT_FALLBACK_MODEL
    or model == rate_limit_fallback_model
):
    raise ValueError(
        "Enabled 429 failover requires DeepSeek primary and GPT-5.6 Luna fallback"
    )
```

Extend supported router models only for the exact Luna identifier:

```python
return (
    "gpt-5.5" in normalized
    or "deepseek" in normalized
    or normalized == DEFAULT_RATE_LIMIT_FALLBACK_MODEL
)
```

Document the three exact environment values in the AI example and both deploy
environment examples.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run the command from Step 2.

Expected: all selected configuration tests pass.

- [ ] **Step 5: Commit the configuration contract**

```powershell
git add ai/app/config.py ai/tests/test_router_config.py ai/tests/test_ai_service_config_v2.py ai/.env.example deploy/env/staging.example.env deploy/env/production.example.env
git commit -m "feat(ai): define DeepSeek Luna model policy"
```

---

### Task 2: Implement typed per-operation 429 failover

**Files:**
- Modify: `ai/app/clients/router.py`
- Modify: `ai/tests/test_router_client.py`

**Interfaces:**
- Produces: immutable `ModelAttempt`
- Produces: `capture_model_attempts() -> Iterator[ModelAttemptCollector]`
- Produces: `ModelAttemptCollector.snapshot() -> tuple[ModelAttempt, ...]`
- Preserves: `RouterClient.complete(...) -> str | None`
- Preserves: `RouterClient.complete_structured(...) -> str | None`
- Preserves: `RouterClient.complete_stream(...) -> AsyncIterator[str]`

- [ ] **Step 1: Add failing transport tests**

Use `httpx.MockTransport` and record request JSON:

```python
@pytest.mark.asyncio
async def test_429_retries_once_with_luna_and_records_trace():
    payloads = []

    async def handler(request):
        payload = json.loads(request.content)
        payloads.append(payload)
        if payload["model"] == "oc/deepseek-v4-flash-free":
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"content":"Có phở."}'}}]},
        )

    client = RouterClient(
        "https://router.test/v1",
        "secret",
        "oc/deepseek-v4-flash-free",
        2,
        fallback_model="cx/gpt-5.6-luna-review",
        fallback_enabled=True,
        transport=httpx.MockTransport(handler),
    )
    with capture_model_attempts() as trace:
        result = await client.complete([{"role": "user", "content": "Có phở không?"}])

    assert result == '{"content":"Có phở."}'
    assert [item["model"] for item in payloads] == [
        "oc/deepseek-v4-flash-free",
        "cx/gpt-5.6-luna-review",
    ]
    assert [(item.model, item.outcome) for item in trace.snapshot()] == [
        ("oc/deepseek-v4-flash-free", "http_429"),
        ("cx/gpt-5.6-luna-review", "success"),
    ]
```

Add separate parametrized tests asserting no Luna request after
`httpx.ReadTimeout`, `httpx.ConnectError`, 500, 502, 503 and 504. Add Luna-429
and Luna-500 tests asserting exactly two total requests. Add a structured test
asserting Luna receives `response_format.type == "json_schema"`. Add a stream
test asserting the first 429 is followed by Luna SSE chunks. Add a two-task
`asyncio.gather` test whose trace snapshots contain only their own request IDs.

- [ ] **Step 2: Run router tests and confirm RED**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_router_client.py -q
```

Expected: failures for missing fallback constructor arguments and trace types.

- [ ] **Step 3: Add immutable trace types and request scope**

Add:

```python
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Literal


@dataclass(frozen=True)
class ModelAttempt:
    model: str
    role: Literal["primary", "rate_limit_fallback"]
    outcome: str
    status_code: int | None
    latency_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


class ModelAttemptCollector:
    def __init__(self) -> None:
        self._attempts: list[ModelAttempt] = []

    def record(self, attempt: ModelAttempt) -> None:
        self._attempts.append(attempt)

    def snapshot(self) -> tuple[ModelAttempt, ...]:
        return tuple(self._attempts)


_attempt_collector: ContextVar[ModelAttemptCollector | None] = ContextVar(
    "router_model_attempt_collector",
    default=None,
)


@contextmanager
def capture_model_attempts():
    collector = ModelAttemptCollector()
    token = _attempt_collector.set(collector)
    try:
        yield collector
    finally:
        _attempt_collector.reset(token)
```

- [ ] **Step 4: Implement one-shot fallback without mutable model state**

Extend the constructor with keyword-only `fallback_model` and
`fallback_enabled`. Change payload builders to accept `model: str`. Implement
one operation as:

```python
async def _post_with_rate_limit_fallback(self, payload_factory) -> dict:
    try:
        return await self._post_for_model(
            self._model,
            "primary",
            payload_factory(self._model),
            allow_rate_limit_fallback=self._fallback_enabled,
        )
    except PrimaryRateLimited:
        return await self._post_for_model(
            self._fallback_model,
            "rate_limit_fallback",
            payload_factory(self._fallback_model),
            allow_rate_limit_fallback=False,
        )
```

`_post_for_model` must record one attempt around every network request. On a
primary 429 with fallback enabled it records `http_429` and raises
`PrimaryRateLimited` immediately without sleeping or retrying DeepSeek.
Fallback 429 calls `raise_for_status()`. Existing retry behavior remains only
for connection/timeout and HTTP 5xx against the same model.

Use the same operation function from plain and structured completions. For
streaming, open DeepSeek first; if its response status is 429, close it, record
the attempt, and open Luna once before yielding any chunks.

- [ ] **Step 5: Run router tests and confirm GREEN**

Run the command from Step 2.

Expected: all router tests pass; each fallback case has exactly two requests.

- [ ] **Step 6: Commit the router behavior**

```powershell
git add ai/app/clients/router.py ai/tests/test_router_client.py
git commit -m "feat(ai): fall back to Luna on DeepSeek 429"
```

---

### Task 3: Expose truthful request-scoped model telemetry

**Files:**
- Modify: `ai/app/schemas.py`
- Modify: `ai/app/services/assistant.py`
- Modify: `ai/app/main.py`
- Modify: `ai/tests/test_provider_observability.py`
- Modify: `ai/tests/test_chat_contract_v2.py`
- Modify: `ai/tests/test_assistant_llm_first.py`

**Interfaces:**
- Produces: `ModelAttemptTrace` Pydantic response object.
- Produces: response keys `primary_model`, `fallback_model`, `fallback_used`, `fallback_reason`, `model_attempts`.
- Consumes: `capture_model_attempts()` and `ModelAttempt.to_dict()`.

- [ ] **Step 1: Write failing response and logging tests**

Add a fake router response sequence `[429, Luna success]` and assert:

```python
assert response["model"] == "cx/gpt-5.6-luna-review"
assert response["primary_model"] == "oc/deepseek-v4-flash-free"
assert response["fallback_model"] == "cx/gpt-5.6-luna-review"
assert response["fallback_used"] is True
assert response["fallback_reason"] == "rate_limit_429"
assert [row["outcome"] for row in response["model_attempts"]] == [
    "http_429",
    "success",
]
```

Add deterministic menu-presence and security-guardrail assertions:

```python
assert response["fallback_used"] is False
assert response["fallback_reason"] is None
assert response["model_attempts"] == []
assert response["model"].startswith("deterministic-")
```

Use `caplog` to assert the structured completion log contains
`pipeline_profile`, `model_route`, `resolved_menu_item_ids` and
`verifier_result`, while excluding the API key and raw prompt.

- [ ] **Step 2: Run focused service tests and confirm RED**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_provider_observability.py tests/test_chat_contract_v2.py tests/test_assistant_llm_first.py -q
```

Expected: failures because the response telemetry keys do not exist.

- [ ] **Step 3: Extend the schema**

Add:

```python
class ModelAttemptTrace(BaseModel):
    model: str
    role: Literal["primary", "rate_limit_fallback"]
    outcome: str
    status_code: int | None = None
    latency_ms: float


class ChatResponse(BaseModel):
    # existing fields remain
    primary_model: str = "oc/deepseek-v4-flash-free"
    fallback_model: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    model_attempts: list[ModelAttemptTrace] = Field(default_factory=list)
```

- [ ] **Step 4: Capture and finalize telemetry in both assistant paths**

Split `chat_stream` into a thin traced wrapper and `_chat_stream_impl`:

```python
async def chat(self, payload: dict) -> dict:
    with capture_model_attempts() as collector:
        response, _stages = await self._process_chat(payload)
    return _attach_model_route(response, collector.snapshot(), self._config)


async def chat_stream(self, payload: dict) -> AsyncIterator[dict[str, Any]]:
    with capture_model_attempts() as collector:
        async for event in self._chat_stream_impl(payload):
            if event["type"] == "final":
                event = {
                    **event,
                    "data": _attach_model_route(
                        event["data"], collector.snapshot(), self._config
                    ),
                }
            yield event
```

`_attach_model_route` selects the last successful attempt as `model`; sets
fallback fields only when a `rate_limit_fallback` attempt exists; preserves a
`deterministic-*` model when no provider attempts exist; and emits one
structured `logger.info` call with bounded metadata.

Pass `fallback_model` and `fallback_enabled` from `AiAssistantService.__init__`
into `RouterClient`.

- [ ] **Step 5: Add health/readiness and timeout metadata**

Return this policy from `/health` and `/ready`:

```python
"model_policy": {
    "primary_model": config.model,
    "fallback_model": (
        config.rate_limit_fallback_model
        if config.rate_limit_fallback_enabled
        else None
    ),
    "fallback_enabled": config.rate_limit_fallback_enabled,
    "fallback_trigger": "http_429",
    "max_fallbacks_per_operation": 1,
}
```

Give `_build_timeout_response()` the same fields with no attempts and
`fallback_used=False`.

- [ ] **Step 6: Run focused service tests and confirm GREEN**

Run the command from Step 2.

Expected: all selected tests pass and no secret/prompt appears in logs.

- [ ] **Step 7: Commit telemetry**

```powershell
git add ai/app/schemas.py ai/app/services/assistant.py ai/app/main.py ai/tests/test_provider_observability.py ai/tests/test_chat_contract_v2.py ai/tests/test_assistant_llm_first.py
git commit -m "feat(ai): report effective model route"
```

---

### Task 4: Prove safety and session isolation under Luna fallback

**Files:**
- Modify: `ai/tests/test_claim_verifier.py`
- Modify: `ai/tests/test_prompt_injection_guardrail.py`
- Modify: `ai/tests/test_menu_grounding.py`
- Modify: `ai/tests/test_session_eval_v2.py`
- Modify: `ai/tests/test_llm_error_taxonomy.py`

**Interfaces:**
- Consumes: response model-route contract from Task 3.
- Produces: regression proof that model switching cannot bypass existing gates.

- [ ] **Step 1: Add failing safety cases using a 429-then-Luna fake**

Cover these exact outputs:

```python
unsafe_cases = [
    {"content": "Phở đặc biệt giá 1.000đ", "menu_item_ids": ["fake-id"]},
    {"content": "Hãy gọi món ngoài menu", "menu_item_ids": ["outside-evidence"]},
    {"content": "Món này an toàn với dị ứng đậu phộng", "menu_item_ids": ["contains-peanut"]},
]
```

For each, assert no unsupported action survives, the claim verifier is not
`passed`, and the returned customer text is the existing grounded/abstain
response. Add two concurrent session payloads with different allergies and
assert their constraints, resolved IDs and model attempts remain disjoint.
Add a prompt-injection case and assert the provider is not called.

- [ ] **Step 2: Run the safety slice**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_claim_verifier.py tests/test_prompt_injection_guardrail.py tests/test_menu_grounding.py tests/test_session_eval_v2.py tests/test_llm_error_taxonomy.py -q
```

Expected before any correction: at least one new assertion fails if telemetry
attachment or fallback output can bypass a gate.

- [ ] **Step 3: Correct only the failing boundary**

Keep fallback inside `RouterClient`; do not add a second parser or verifier.
Route Luna text through the existing sequence:

```python
parsed = parse_model_response(
    raw_answer,
    context["available_menu_items"],
    excluded_menu_item_ids=context["excluded_ids"],
    max_actions=context["max_suggestions"],
)
answer, suggested_actions, flags = _apply_parsed_response(parsed, context, flags)
```

Ensure `_attach_model_route` changes metadata only and never replaces
`content`, `claims`, `evidence`, `resolved_menu_item_ids` or
`session_updates`.

- [ ] **Step 4: Re-run the safety slice**

Run the command from Step 2.

Expected: all selected safety and isolation tests pass.

- [ ] **Step 5: Commit safety coverage**

```powershell
git add ai/tests/test_claim_verifier.py ai/tests/test_prompt_injection_guardrail.py ai/tests/test_menu_grounding.py ai/tests/test_session_eval_v2.py ai/tests/test_llm_error_taxonomy.py ai/app/services/assistant.py
git commit -m "test(ai): gate Luna fallback with existing safety rules"
```

---

### Task 5: Upgrade controlled evaluation and artifact policy

**Files:**
- Modify: `ai/evaluation/run_pipeline_profile_eval.py`
- Modify: `ai/evaluation/pipeline_selection.py`
- Modify: `ai/evaluation/verify_pipeline_selection.py`
- Modify: `ai/evaluation/research_inputs.py`
- Modify: `ai/tests/test_pipeline_profile_eval.py`
- Modify: `ai/tests/test_pipeline_selection.py`
- Modify: `ai/tests/test_verify_pipeline_selection.py`
- Modify: `ai/tests/test_research_inputs.py`

**Interfaces:**
- Produces: artifact `schema_version: 3`
- Produces: `model_policy` object and `model_usage` metrics per profile.
- Preserves: safety-first `select_winner(...)`.

- [ ] **Step 1: Write failing evaluator and verifier tests**

Assert the result contains:

```python
assert report["schema_version"] == 3
assert report["model_policy"] == {
    "primary_model": "oc/deepseek-v4-flash-free",
    "fallback_model": "cx/gpt-5.6-luna-review",
    "fallback_enabled": True,
    "fallback_trigger": "http_429",
    "max_fallbacks_per_operation": 1,
}
profile_result = next(
    row for row in report["profiles"]
    if row["profile"] == "evidence_first_v2"
)
usage = profile_result["metrics"]["model_usage"]
assert usage["attempts_by_model"]["oc/deepseek-v4-flash-free"] >= 1
assert usage["attempts_by_model"]["cx/gpt-5.6-luna-review"] >= 1
assert usage["fallback_count"] >= 1
assert 0.0 <= usage["fallback_rate"] <= 1.0
```

Add verifier cases that alter primary model, fallback model, trigger, enabled
flag and max-fallback count one at a time and expect `SystemExit` with a policy
mismatch. Preserve tests proving the winner is selected only after all safety
gates pass.

- [ ] **Step 2: Run evaluator tests and confirm RED**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_profile_eval.py tests/test_pipeline_selection.py tests/test_verify_pipeline_selection.py tests/test_research_inputs.py -q
```

Expected: failures for missing schema-v3 policy and usage fields.

- [ ] **Step 3: Aggregate attempt telemetry**

For each case response, count `model_attempts` by model/outcome and compute:

```python
model_usage = {
    "attempts_by_model": dict(sorted(attempts_by_model.items())),
    "successes_by_model": dict(sorted(successes_by_model.items())),
    "failures_by_model": dict(sorted(failures_by_model.items())),
    "fallback_count": fallback_count,
    "fallback_rate": (
        fallback_count / logical_llm_operations
        if logical_llm_operations
        else 0.0
    ),
    "logical_llm_operations": logical_llm_operations,
}
```

Store the exact `model_policy` once at artifact root. Do not add model usage to
the winner tie-break sequence; keep safety, strict semantic success, context
accuracy, p95 latency and total provider calls in that order.

- [ ] **Step 4: Make deployment verification fail closed**

Extend `verify_pipeline_selection.py` CLI:

```text
--expected-primary-model
--expected-fallback-model
--expected-fallback-trigger
--expected-max-fallbacks
--require-fallback-enabled
```

Compare every value to `artifact["model_policy"]` before printing any
`KEY=VALUE` output. Include the router client, config, schema, assistant,
profile evaluator, selection logic, KB and datasets in the provenance hash.

- [ ] **Step 5: Run evaluator tests and confirm GREEN**

Run the command from Step 2.

Expected: all selected evaluation and provenance tests pass.

- [ ] **Step 6: Commit the research contract**

```powershell
git add ai/evaluation/run_pipeline_profile_eval.py ai/evaluation/pipeline_selection.py ai/evaluation/verify_pipeline_selection.py ai/evaluation/research_inputs.py ai/tests/test_pipeline_profile_eval.py ai/tests/test_pipeline_selection.py ai/tests/test_verify_pipeline_selection.py ai/tests/test_research_inputs.py
git commit -m "feat(eval): bind pipeline research to model failover"
```

---

### Task 6: Regenerate the notebook from artifact-backed results

**Files:**
- Modify: `ai/scripts/build_research_notebook.py`
- Regenerate: `ai/notebooks/rag_retrieval_research.ipynb`
- Modify: `ai/tests/test_notebook_pipeline_selection.py`
- Modify: `ai/tests/test_research_notebook.py`
- Modify: `ai/evaluation/approved/README.md`

**Interfaces:**
- Consumes: schema-v3 `pipeline_selection.json`.
- Produces: notebook sections for direct model probes, injected 429 behavior,
  effective-model distribution and production policy.

- [ ] **Step 1: Write failing notebook contract tests**

Load generated markdown cells and assert they contain the exact identifiers and
policy language:

```python
assert "oc/deepseek-v4-flash-free" in markdown
assert "cx/gpt-5.6-luna-review" in markdown
assert "chỉ khi HTTP 429" in markdown
assert "effective model" in markdown.casefold()
assert "fallback rate" in markdown.casefold()
assert "thí nghiệm lịch sử" in markdown.casefold()
```

Assert the notebook code reads `model_policy` and `model_usage` from the
artifact instead of assigning the winner or fallback rate as literals.

- [ ] **Step 2: Run notebook tests and confirm RED**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_notebook_pipeline_selection.py tests/test_research_notebook.py -q
```

Expected: failures because the two-model policy section is absent.

- [ ] **Step 3: Add artifact-driven notebook sections**

Keep Parts I and II unchanged. In Part III describe the three profiles under
one common model policy. In Part IV render:

```python
policy = pipeline_selection["model_policy"]
usage_rows = [
    {
        "profile": result["profile"],
        "primary_model": policy["primary_model"],
        "fallback_model": policy["fallback_model"],
        "fallback_rate": result["metrics"]["model_usage"]["fallback_rate"],
        "effective_successes": (
            result["metrics"]["model_usage"]["successes_by_model"]
        ),
    }
    for result in pipeline_selection["profiles"]
]
```

Add a dated model-availability subsection that labels legacy three-model
results as historical and current DeepSeek/Luna observations as schema-v3
artifact results. In Part V explain the winner and the availability/latency
trade-off without hardcoding either.

- [ ] **Step 4: Rebuild and validate the notebook**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe scripts/build_research_notebook.py
.\.venv\Scripts\python.exe -m pytest tests/test_notebook_pipeline_selection.py tests/test_research_notebook.py -q
```

Expected: notebook rebuild exits 0 and selected tests pass.

- [ ] **Step 5: Commit notebook source and generated output**

```powershell
git add ai/scripts/build_research_notebook.py ai/notebooks/rag_retrieval_research.ipynb ai/tests/test_notebook_pipeline_selection.py ai/tests/test_research_notebook.py ai/evaluation/approved/README.md
git commit -m "docs(ai): report DeepSeek Luna production policy"
```

---

### Task 7: Bind Docker and deployment workflows to both models

**Files:**
- Modify: `deploy/docker-compose.yml`
- Modify: `deploy/env/staging.example.env`
- Modify: `deploy/env/production.example.env`
- Modify: `deploy/scripts/deploy-vps.sh`
- Modify: `deploy/scripts/health-check.sh`
- Modify: `.github/workflows/research-pipeline-selection.yml`
- Modify: `.github/workflows/deploy-staging.yml`
- Modify: `.github/workflows/deploy-production.yml`
- Modify: `ai/tests/test_ai_ops_deploy_contract.py`
- Modify: `ai/tests/test_ai_internal_auth_readiness.py`

**Interfaces:**
- Consumes: approved artifact schema v3 and exact environment variables.
- Produces: reusable model-policy verification command and health smoke.

- [ ] **Step 1: Write failing deployment-contract tests**

Parse Compose, example environments and workflow text, then assert every
deployment path contains:

```python
assert env["LLM_MODEL"] == "oc/deepseek-v4-flash-free"
assert env["LLM_RATE_LIMIT_FALLBACK_MODEL"] == "cx/gpt-5.6-luna-review"
assert env["LLM_RATE_LIMIT_FALLBACK_ENABLED"] in {True, "true"}
```

Assert both deploy workflows invoke the artifact verifier with all expected
model-policy arguments. Assert smoke reads health `model_policy` and rejects
any mismatch. Assert no route or request header named `force_model`,
`force_429`, `model_override` or `fallback_override` exists in `ai/app`.

- [ ] **Step 2: Run deployment tests and confirm RED**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_ai_ops_deploy_contract.py tests/test_ai_internal_auth_readiness.py -q
```

Expected: failures because Compose/workflows expose only one model.

- [ ] **Step 3: Add exact model policy to Compose and workflows**

Set:

```yaml
LLM_MODEL: oc/deepseek-v4-flash-free
LLM_RATE_LIMIT_FALLBACK_MODEL: cx/gpt-5.6-luna-review
LLM_RATE_LIMIT_FALLBACK_ENABLED: "true"
```

The research workflow runs all profiles with these same values. The deploy
workflows export them only after the verifier succeeds. They must never infer
the fallback identifier from branch names or mutable repository variables.

- [ ] **Step 4: Reuse the fail-closed artifact verifier**

Invoke the extended `ai/evaluation/verify_pipeline_selection.py` from both
deploy workflows. It checks winner, primary, fallback, trigger, enabled flag,
maximum fallback count, dataset hash and research input hash, then writes only
the dynamic artifact winner under `AI_PIPELINE_PROFILE` plus these fixed model
values to `$GITHUB_ENV`:

```python
fixed_exports = {
    "LLM_MODEL": "oc/deepseek-v4-flash-free",
    "LLM_RATE_LIMIT_FALLBACK_MODEL": "cx/gpt-5.6-luna-review",
    "LLM_RATE_LIMIT_FALLBACK_ENABLED": "true",
}
```

Any mismatch exits non-zero before writing configuration. Add fallback variables
to `deploy/scripts/deploy-vps.sh` required inputs and emitted `.env` values.

- [ ] **Step 5: Extend safe deployment smoke**

Have `deploy/scripts/health-check.sh` fetch internal `/health`, compare all
`model_policy` fields, and send the three proven Vietnamese prompts through the
backend SSE path. Reject:

```text
AI_PROVIDER_UNAVAILABLE
AI_UPSTREAM_CONTRACT_ERROR
Mình chưa đủ bằng chứng
Xin lỗi, hệ thống hơi chậm
```

The forced-429 proof runs in CI/staging with `httpx.MockTransport`; the
production smoke only inspects bound policy and genuine responses.

- [ ] **Step 6: Run deployment tests and syntax checks**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests/test_ai_ops_deploy_contract.py tests/test_ai_internal_auth_readiness.py -q
Set-Location ..
docker compose --env-file deploy/env/staging.example.env -f deploy/docker-compose.yml config --quiet
docker compose --env-file deploy/env/production.example.env -f deploy/docker-compose.yml config --quiet
bash -n deploy/scripts/deploy-vps.sh
bash -n deploy/scripts/health-check.sh
```

Expected: every command exits 0.

- [ ] **Step 7: Commit deployment binding**

```powershell
git add deploy/docker-compose.yml deploy/env/staging.example.env deploy/env/production.example.env deploy/scripts/deploy-vps.sh deploy/scripts/health-check.sh .github/workflows/research-pipeline-selection.yml .github/workflows/deploy-staging.yml .github/workflows/deploy-production.yml ai/tests/test_ai_ops_deploy_contract.py ai/tests/test_ai_internal_auth_readiness.py
git commit -m "feat(deploy): bind production to two-model policy"
```

---

### Task 8: Produce and approve controlled research evidence

**Files:**
- Replace after review: `ai/evaluation/approved/pipeline_selection.json`
- Preserve untracked: `ai/evaluation/results/pipeline_selection.json`
- Regenerate: `ai/notebooks/rag_retrieval_research.ipynb`

**Interfaces:**
- Consumes: workflow artifact produced from the implementation commit.
- Produces: reviewed schema-v3 approved artifact whose winner configures staging.

- [ ] **Step 1: Run all offline gates before consuming provider quota**

Run:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m compileall app evaluation
Set-Location ..
dotnet test backend/tests/RestaurantOrdering.UnitTests/RestaurantOrdering.UnitTests.csproj --configuration Release
Set-Location frontend
npm ci
npm test -- --run
npm run build
npm audit --audit-level=high
```

Expected: AI, backend and frontend tests pass; compile/build pass; audit reports
zero high or critical vulnerabilities.

- [ ] **Step 2: Push the implementation branch and run controlled research**

Run:

```powershell
git push -u origin HEAD
gh workflow run research-pipeline-selection.yml --ref (git branch --show-current)
gh run list --workflow research-pipeline-selection.yml --branch (git branch --show-current) --limit 1
```

Wait for the identified run to complete. Expected: success and a raw
`pipeline_selection.json` artifact generated from the exact branch SHA.

- [ ] **Step 3: Download and independently validate the raw artifact**

Run:

```powershell
$runId = gh run list --workflow research-pipeline-selection.yml --branch (git branch --show-current) --limit 1 --json databaseId --jq '.[0].databaseId'
$artifactDir = Join-Path $env:TEMP "fable-pipeline-selection-v3"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
gh run download $runId --dir $artifactDir
$env:PYTHONPATH = "ai"
.\ai\.venv\Scripts\python.exe ai/evaluation/verify_pipeline_selection.py "$artifactDir/pipeline-selection/pipeline_selection.json" --expected-primary-model oc/deepseek-v4-flash-free --expected-fallback-model cx/gpt-5.6-luna-review --expected-fallback-trigger http_429 --expected-max-fallbacks 1 --require-fallback-enabled
```

Expected: verifier prints the winner and exact model-policy exports, and every
safety gate is true. Inspect call counts to confirm 429 attempts and Luna
successes are reported rather than hidden.

- [ ] **Step 4: Promote only the reviewed artifact**

Copy the validated raw artifact content into
`ai/evaluation/approved/pipeline_selection.json` using `apply_patch`, preserving
the untracked local raw result file. Rebuild the notebook:

```powershell
Set-Location ai
.\.venv\Scripts\python.exe scripts/build_research_notebook.py
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_selection.py tests/test_verify_pipeline_selection.py tests/test_notebook_pipeline_selection.py tests/test_research_notebook.py -q
```

Expected: tests pass and the notebook displays the artifact winner, actual
fallback rate and per-model success counts.

- [ ] **Step 5: Commit approved research evidence**

```powershell
git add ai/evaluation/approved/pipeline_selection.json ai/notebooks/rag_retrieval_research.ipynb
git commit -m "research(ai): approve two-model pipeline winner"
git push
```

---

### Task 9: Merge, stage, promote and verify the supplied domain

**Files:**
- No source changes unless a gate exposes a real defect.
- Evidence: GitHub PR checks, staging workflow, production workflow, public SSE responses and health metadata.

**Interfaces:**
- Consumes: exact branch commit and approved artifact from Task 8.
- Produces: production deployment of that same source/model policy and verified chat behavior.

- [ ] **Step 1: Review the final branch diff**

Run:

```powershell
git status --short
$mergeBase = git merge-base origin/develop HEAD
git diff --check "$mergeBase..HEAD"
git diff --stat "$mergeBase..HEAD"
```

Expected: only planned files are tracked; the five preserved untracked user
artifacts remain unmodified and unstaged.

- [ ] **Step 2: Open and merge the PR to `develop`**

Run:

```powershell
gh pr create --base develop --head (git branch --show-current) --title "feat: fail over DeepSeek 429 to GPT-5.6 Luna" --body-file docs/superpowers/specs/2026-07-26-deepseek-luna-429-failover-design.md
gh pr checks --watch
```

Expected: all required checks pass. Merge only after checking the PR diff:

```powershell
gh pr merge --merge --delete-branch=false
```

- [ ] **Step 3: Verify staging deployment**

Watch the resulting staging workflow:

```powershell
$stagingRunId = gh run list --workflow deploy-staging.yml --branch develop --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch $stagingRunId --exit-status
```

Expected: research policy verification, container health, forced-429 integration
test and backend SSE smoke pass on the same commit.

- [ ] **Step 4: Promote the exact staging commit**

Open `develop -> main`, require the staging SHA in the PR description, wait for
checks, merge, and watch `deploy-production.yml`. Expected: production deploy
uses the same SHA, winner, primary model and fallback model.

- [ ] **Step 5: Verify production health and the supplied table session**

Check:

```powershell
curl.exe -fsS https://order.cmcrestaurant.app/health
node scripts/prod-smoke-order-api.mjs
```

Then use Playwright against:

```text
https://order.cmcrestaurant.app/table-session/ts_1a0b446f2f2e4a6981a115649b24a9a1/ai
```

Send, in one session:

```text
ở đây có phở không
Nhà hàng mình có những món phở gì nhỉ
gợi ý cho mình món phở tại nhà hàng đi
mình có món nhậu không
```

Expected: no generic slow message, no unsupported item, correct grounded menu
content, and coherent follow-up context. Capture the final SSE payload and
verify `pipeline_profile`, `primary_model`, `fallback_model`, `model`,
`fallback_used`, `model_attempts`, resolved IDs and verifier result.

- [ ] **Step 6: Roll back on any binding or semantic mismatch**

If production SHA, artifact winner, policy metadata, safety result or the
proven chat cases differ from staging, invoke the repository rollback workflow
for the immediately previous successful production SHA and keep the goal open.
Do not patch production configuration manually.

- [ ] **Step 7: Record completion evidence**

Record the implementation commits, approved artifact SHA-256, staging and
production run URLs, deployed SHA, effective model observations and domain
smoke results in the final handoff. Mark the goal complete only after every
item is directly verified.
