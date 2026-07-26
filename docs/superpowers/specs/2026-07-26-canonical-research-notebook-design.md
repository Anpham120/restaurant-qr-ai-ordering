# Canonical Research Notebook Design

## Goal

Create a new Vietnamese research notebook that explains the restaurant AI system as one reproducible argument: data and evidence, retrieval, pipeline alternatives, controlled evaluation, architecture selection, and production binding. The current notebook remains untouched as a presentation reference until the new notebook is approved by the project owner.

## Non-negotiable constraints

- The notebook is written in UTF-8 and must render Vietnamese correctly.
- One canonical research bundle is used throughout all experiments: the same KB snapshot, menu fixture, case catalog, model policy, prompt budget, and scorer rules.
- Retrieval, single-turn, multi-turn, safety, and availability are views of one case catalog, not unrelated test datasets.
- Historical artifacts that used another dataset may be shown only as historical context and cannot select the production pipeline.
- Every chart and numeric table is followed by an explicit observation, interpretation, limitation, and next decision.
- No pipeline winner is hardcoded. The notebook reads the approved `pipeline_selection.json` artifact and displays `DEPLOY BLOCKED` when no candidate passes the hard gate.
- Production is bound only to the approved winner profile. DeepSeek is primary; Luna is eligible only for a single `http_429` fallback attempt.
- The prior notebook is preserved until the owner explicitly approves the new notebook. Cleanup happens only afterwards and only for proven-unused files.

## New notebook artifact

- New path: `ai/notebooks/restaurant_ai_research_report.ipynb`
- Legacy reference: `ai/notebooks/rag_retrieval_research.ipynb`
- Builder: new focused generator under `ai/scripts/` rather than incremental mutation of the legacy notebook.
- Validation: a dedicated notebook contract test checks UTF-8 content, ordered parts, canonical-data markers, executable-code visibility, and artifact-driven production conclusion.

## Canonical data contract

The data layer has one manifest and a deterministic hash. Each case records its input, expected evidence, expected IDs, expected route, expected safety behavior, expected context/state transition, and fixture references.

```json
{
  "case_id": "menu-pho-list-01",
  "scenario": "single_turn",
  "query": "Nhà hàng mình có những món phở gì nhỉ?",
  "history": [],
  "session_state": {},
  "live_context_fixture": "menu-v1",
  "expected_evidence_ids": [],
  "expected_menu_item_ids": [],
  "expected_route": "live_data",
  "safety_expectations": [],
  "context_expectations": []
}
```

`scenario` labels such as `retrieval`, `single_turn`, `multi_turn`, `safety`, and `availability` produce filtered views. They do not introduce a new data source. The manifest records `knowledge_base_hash`, `menu_fixture_hash`, `dataset_hash`, and `catalog_version`.

## Narrative structure

### Part I — Data, domain, and evidence contract

Purpose: establish what the system is allowed to know and what all later experiments will use.

Sections:

1. Restaurant AI problem, unsafe outcomes, and research questions.
2. Full KB inventory: one visible row per real Markdown file with filename, curated topic, business purpose, representative customer questions, risk tier, and chunk count.
3. Menu fixture inventory: categories, prices, tags, availability, allergens, and product-ID integrity.
4. Vietnamese text characteristics: diacritics, teencode, no-diacritics, vocabulary variation, and normalization method.
5. Canonical case catalog: schema, scenario distribution, and case-to-evidence coverage.
6. Data quality checks: duplicate cases, missing expectations, invalid IDs, unavailable items, and missing evidence.

Charts:

- Plotly treemap for KB topic hierarchy.
- Seaborn horizontal bar chart for files and chunks by topic.
- Stacked risk-tier chart.
- Heatmap for topic × scenario coverage.
- Sankey diagram from case scenario to evidence source to expected route.
- Menu category/tag/allergen charts and data-quality matrix.

Part conclusion: freeze the canonical manifest and hashes before measuring retrieval or pipeline quality.

### Part II — Retrieval methods on the canonical bundle

Purpose: compare BM25, Dense E5, and Hybrid RRF using the same canonical retrieval-labelled rows.

Sections:

1. Retrieval question and fair comparison protocol.
2. BM25 construction and Vietnamese normalization.
3. Dense E5 construction and embedding assumptions.
4. Hybrid RRF construction.
5. Results, error analysis, latency, and evidence coverage.

Charts:

- Grouped Hit@1/Hit@5 bars.
- Heatmap for method × query variant performance.
- Box/violin latency chart.
- Error-category chart and representative case table.

Part conclusion: select retrieval as evidence infrastructure, not as a shortcut to choose the conversational pipeline.

### Part III — Pipeline construction and candidate profiles

Purpose: show how evidence, live menu data, safety, and conversation state form a complete response.

Sections:

1. Common evidence assembly shared by every profile.
2. Guardrails, claim verification, and fail-closed behavior.
3. LiveContext, typed state, rolling summary, and state transitions.
4. The three candidate profiles: `llm_first_v1`, `evidence_first_v2`, `planner_state_v3`.
5. Unit and integration demonstrations against canonical cases.

Charts:

- NetworkX pipeline/evidence graph.
- Route-distribution stacked bars.
- Guardrail coverage matrix.
- Multi-turn state-transition timeline.

Part conclusion: all profiles share the same boundaries and input data; only their orchestration differs.

### Part IV — Controlled evaluation and architecture selection

Purpose: compare profiles fairly and choose a winner using the required order: safety, quality, context, latency, then LLM calls.

Sections:

1. Fixed evaluation protocol: canonical manifest, DeepSeek primary, Luna fallback on one HTTP 429, prompt budget, three LLM repetitions, deterministic single execution.
2. Hard-gate results: unsupported claims, allergy/ID/price/session isolation, out-of-evidence items, and generated-fact persistence.
3. Quality and context measurements.
4. Latency, DeepSeek/Luna attempts, and fallback rate.
5. `pipeline_selection.json`: winner, rationale, model policy, commit, hashes, and timestamp.

Charts:

- Hard-gate pass/fail matrix.
- Strict semantic success and context-accuracy bars.
- P95 latency box/range chart.
- LLM-attempt and fallback-rate chart.
- Plotly radar only as a secondary summary, never as the selector.

Part conclusion: only an artifact winner that passes the hard gate may become the production profile.

### Part V — Production binding, staging proof, and operational limits

Purpose: demonstrate that production follows the selected research result exactly.

Sections:

1. Winner artifact to `AI_PIPELINE_PROFILE` binding.
2. DeepSeek/Luna model policy and fallback limitation.
3. Internal telemetry: pipeline profile, model attempts, route, resolved IDs, evidence, verifier outcome, and state transition.
4. Staging smoke and production smoke cases using the three customer questions.
5. Rollback conditions and remaining limitations.

Charts:

- NetworkX lineage graph: input manifest → selection artifact → deploy configuration → telemetry.
- Deployment state/rollback decision chart.

Part conclusion: production is not an independent architecture; it is the winner profile operating on the same research contract.

## Presentation conventions

Every substantive section follows this order:

1. Research or engineering question.
2. Method and controlled assumptions.
3. Readable executable code.
4. Table or chart built from the code/artifact.
5. `Nhận xét` with observed result, interpretation, limitation, and resulting decision.
6. A transition paragraph that explains why the next section exists.

Charts use `pandas`, `matplotlib`, `seaborn`, `plotly`, and `networkx` where each library makes the relationship clearer. No chart is included merely for decoration.

## Cleanup protocol after approval

1. Build, execute where feasible, validate, and render the new notebook.
2. Owner reviews and approves the new notebook.
3. Generate an inventory of legacy notebooks, duplicate copies, temporary directories, stale generated artifacts, and orphan helper scripts.
4. Prove each candidate is not referenced by Python code, CI, deployment, docs, or the approved notebook.
5. Remove only approved/proven-unused targets; preserve the old notebook until owner approval, then delete it in a separate, reviewable change.

