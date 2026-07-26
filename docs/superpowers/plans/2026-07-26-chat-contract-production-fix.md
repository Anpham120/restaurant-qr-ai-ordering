# Chat Contract Production Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore browser-facing AI chat and make deployment fail whenever the backend-to-Python contract is invalid.

**Architecture:** Keep Python's typed V2 schema strict and normalize missing state at the backend producer. Preserve direct Python research/profile smoke checks, then add a real backend SSE smoke to cover the UI data path.

**Tech Stack:** .NET 8 minimal API, Python 3.12/FastAPI/Pydantic, Bash deployment scripts, Docker Compose, GitHub Actions.

## Global Constraints

- Production LLM remains `oc/deepseek-v4-flash-free` through 9router.
- Production profile remains bound to the winner in `pipeline_selection.json`.
- GPT must not be added as a fallback.
- Existing untracked user files must not be staged or modified.

---

### Task 1: Non-null conversation-frame contract

**Files:**
- Modify: `backend/src/RestaurantQrAiOrdering.Api/Chat/ChatAiProvider.cs`
- Test: `backend/tests/RestaurantQrAiOrdering.Api.Tests/ChatAiProviderTests.cs`

**Interfaces:**
- Consumes: `ChatSessionStateSnapshot.ConversationFrame`
- Produces: V2 JSON where `session_state.conversation_frame` is always an object

- [ ] **Step 1: Write the failing test**

Add a provider test that sends a request with a non-null session state and a
null conversation frame, captures the outgoing JSON, and asserts:

```csharp
payload.GetProperty("session_state")
    .GetProperty("conversation_frame")
    .ValueKind.Should().Be(JsonValueKind.Object);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj -c Release --filter ConversationFrame
```

Expected: FAIL because `conversation_frame` is JSON null.

- [ ] **Step 3: Write minimal implementation**

Add one backend default-frame factory and use:

```csharp
persistedState?.ConversationFrame ?? CreateDefaultConversationFrame()
```

when constructing `ChatSessionStatePayload`.

- [ ] **Step 4: Run test to verify it passes**

Run the same filtered command. Expected: PASS.

### Task 2: Upstream contract-error observability

**Files:**
- Modify: `backend/src/RestaurantQrAiOrdering.Api/Chat/ChatAiProvider.cs`
- Test: `backend/tests/RestaurantQrAiOrdering.Api.Tests/ChatAiProviderTests.cs`

**Interfaces:**
- Consumes: non-success Python HTTP response
- Produces: safe fallback plus `AI_UPSTREAM_CONTRACT_ERROR` for HTTP 4xx

- [ ] **Step 1: Write a failing 422 test**

Configure the fake Python handler to return HTTP 422 with a Pydantic body and
assert the customer response excludes the raw body while guardrails contain
`AI_UPSTREAM_CONTRACT_ERROR`.

- [ ] **Step 2: Verify RED**

Run the filtered provider test and confirm it fails because all non-success
responses currently use only `AI_PROVIDER_UNAVAILABLE`.

- [ ] **Step 3: Implement bounded logging and classification**

Read at most 2,048 characters from the upstream body for structured server
logging and classify 4xx responses as contract errors. Keep customer copy
generic.

- [ ] **Step 4: Verify GREEN**

Run all `ChatAiProviderTests`.

### Task 3: Align timeout budgets

**Files:**
- Modify: `deploy/docker-compose.yml`
- Test: `backend/tests/RestaurantQrAiOrdering.Api.Tests/DeploymentConfigurationTests.cs`

**Interfaces:**
- Produces: `BACKEND_AI_TIMEOUT_SECONDS=18` by default

- [ ] **Step 1: Write a failing configuration assertion**

Assert the Compose API environment default is 18 seconds and exceeds the
14-second Python request budget.

- [ ] **Step 2: Verify RED**

Run the deployment configuration test. Expected: FAIL with current value 12.

- [ ] **Step 3: Change the Compose default to 18**

Update only the backend timeout default.

- [ ] **Step 4: Verify GREEN**

Run deployment configuration tests and `docker compose config`.

### Task 4: Add browser-path deployment smoke

**Files:**
- Modify: `deploy/scripts/health-check.sh`
- Test: `backend/tests/RestaurantQrAiOrdering.Api.Tests/DeploymentConfigurationTests.cs`

**Interfaces:**
- Consumes: public `/api/chat/sessions` and `/messages/stream`
- Produces: deployment failure when the real backend-to-Python path falls back

- [ ] **Step 1: Write a failing script-contract test**

Assert the script creates a backend chat session, uses its returned capability
token, calls `/messages/stream`, and rejects provider/contract-error flags.

- [ ] **Step 2: Verify RED**

Run the deployment configuration test. Expected: FAIL because only direct
Python probes exist.

- [ ] **Step 3: Implement the backend SSE smoke**

Create a temporary standalone chat session through the backend API, send
`ở đây có phở không`, parse SSE final data, and assert a non-empty assistant
message with no unavailable/contract-error flags or slow fallback.

- [ ] **Step 4: Verify GREEN**

Run the deployment test and `bash -n deploy/scripts/health-check.sh`.

### Task 5: Full validation and rollout

**Files:**
- Validate: backend, AI, frontend, notebook, workflows, Compose
- Deploy: staging then production through protected PRs

- [ ] **Step 1: Run full local verification**

Run Release backend tests, all AI tests, frontend tests/build, notebook
validation, workflow YAML parsing, shell syntax, Compose config, and security
audits.

- [ ] **Step 2: Commit and push**

Stage only files owned by this fix, review the diff, commit, and push the fix
branch.

- [ ] **Step 3: Roll out staging**

Merge through the protected develop PR, wait for staging, and verify the backend
SSE smoke passes on the staged commit.

- [ ] **Step 4: Roll out production**

Promote develop through the protected main PR. Allow deployment only when the
DeepSeek profile artifact still selects `evidence_first_v2` and all health
gates pass.

- [ ] **Step 5: Retest the reported session**

Send `ở đây có phở không` through the exact table session and confirm the reply
contains grounded menu evidence rather than the slow fallback.

