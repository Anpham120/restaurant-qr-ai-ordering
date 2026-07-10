# Academic RAG chatbot v2

This service answers restaurant questions from two controlled sources: the live menu supplied by the .NET API and the versioned policy snapshot in `data/policies.json`. It never mutates a cart or order. Suggested actions contain canonical menu IDs and must be confirmed by the customer; the backend validates ID, price and availability again.

## Runtime flow

1. The backend reads every current menu item from PostgreSQL and sends it with the latest six chat messages.
2. The service fingerprints the menu and rebuilds its in-memory index only when the menu changes.
3. The selected retriever in `research/artifacts/production_config.json` ranks menu and policy documents.
4. Deterministic fast paths answer guardrail, availability, price, policy and explicit-order requests without an LLM call.
5. Other grounded questions may use Gemini Flash through 9Router to write a short response. If the provider fails or times out, the service returns a retrieval-only answer.
6. The backend canonicalizes suggested actions from its own database before returning them to the UI.

The current production retriever is TF-IDF because it won the locked test under the preregistered selection rule. RAG here means retrieval-augmented generation; it does not require a vector database. Dense embedding and hybrid alternatives are retained in the reproducible study rather than asserted to be better.

## Run locally

```bash
cd ai
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

```env
AI_PROVIDER=9router
AI_BASE_URL=http://127.0.0.1:20128/v1
AI_MODEL=gc/gemini-3-flash
AI_API_KEY=replace-with-9router-key
AI_TIMEOUT_SECONDS=7
AI_MAX_OUTPUT_TOKENS=220
AI_POLICIES_PATH=data/policies.json
RAG_PRODUCTION_CONFIG_PATH=research/artifacts/production_config.json
RAG_TOP_K=5
```

Without `AI_API_KEY`, retrieval and every deterministic fast path continue to work; only generative phrasing is disabled.

## API

- `GET /health`
- `POST /v1/retrieval/search`
- `POST /v1/chat`

Both POST endpoints require the current menu in the request. This prevents a stale, duplicated menu knowledge base from becoming production truth.

## Verification

```bash
PYTHONPATH=ai python -m unittest discover -s ai/tests -v
python -m pip install -r ai/requirements-research.txt
PYTHONPATH=ai python ai/research/build_dataset.py
PYTHONPATH=ai python ai/research/run_experiments.py
MPLCONFIGDIR=/tmp/matplotlib PYTHONPATH=ai python ai/research/build_notebook.py
```

See `research/README.md` and `notebooks/academic_retrieval_study.ipynb` for the protocol, raw artifacts, statistical tests and limitations.
