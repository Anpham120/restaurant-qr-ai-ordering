# %% [markdown]
# # CMC Restaurant AI/RAG Research Protocol
#
# Notebook này là khuôn nghiên cứu bắt buộc trước khi kết luận cấu hình RAG nào tốt hơn.
# Không kết luận BM25, embedding hay hybrid theo cảm tính; mọi nhận định phải dựa trên
# cùng một golden set, cùng metric, và cùng điều kiện chạy.

# %% [markdown]
# ## 1. Research Questions
#
# - BM25 có đủ tốt cho câu hỏi thực đơn/chính sách ngắn không?
# - Embedding có cải thiện câu hỏi diễn đạt tự nhiên, đồng nghĩa, hoặc nhiều ý không?
# - Hybrid BM25 + embedding có tăng hit@5 mà vẫn giữ latency đủ nhanh không?
# - Chat memory theo `TableSession` có giữ ngữ cảnh sau refresh không?
# - Khi đóng phiên bàn, memory có được xóa để tránh rò dữ liệu khách cũ không?

# %%
from pathlib import Path
import csv
import json
import statistics
import time

PROJECT_ROOT = Path.cwd().resolve().parents[1] if Path.cwd().name == "notebooks" else Path.cwd().resolve()
AI_ROOT = PROJECT_ROOT / "ai"
GOLDEN_PATH = AI_ROOT / "evaluation" / "golden_questions.csv"
KB_PATH = AI_ROOT / "knowledge-base"

# %% [markdown]
# ## 2. Load Golden Set

# %%
def load_golden_cases(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

golden_cases = load_golden_cases(GOLDEN_PATH)
len(golden_cases), golden_cases[:3]

# %% [markdown]
# ## 3. Experiment Matrix
#
# Fill each retrieval function with the real implementation under test.
# Each function must return:
#
# ```python
# {
#   "answer": "...",
#   "sources": ["menu.md", "faq.md"],
#   "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
#   "latency_ms": 123.4,
# }
# ```

# %%
def run_bm25(question: str):
    raise NotImplementedError("Wire to current lexical retriever")

def run_embedding(question: str):
    raise NotImplementedError("Wire to embedding retriever")

def run_hybrid(question: str):
    raise NotImplementedError("Wire to BM25 + embedding rerank")

EXPERIMENTS = {
    "bm25": run_bm25,
    "embedding": run_embedding,
    "hybrid": run_hybrid,
}

# %% [markdown]
# ## 4. Metrics

# %%
def split_expected(value: str):
    return [item.strip() for item in value.split(";") if item.strip()]

def score_case(case, result):
    expected_sources = set(split_expected(case["expected_sources"]))
    expected_flags = set(split_expected(case["expected_guardrail_flags"]))
    actual_sources = set(result.get("sources", []))
    actual_flags = set(result.get("guardrail_flags", []))

    source_hit = not expected_sources or bool(expected_sources & actual_sources)
    guardrail_hit = expected_flags <= actual_flags

    return {
        "case_id": case["case_id"],
        "source_hit": source_hit,
        "guardrail_hit": guardrail_hit,
        "latency_ms": float(result.get("latency_ms", 0)),
        "expected_sources": sorted(expected_sources),
        "actual_sources": sorted(actual_sources),
        "expected_flags": sorted(expected_flags),
        "actual_flags": sorted(actual_flags),
    }

def summarize_scores(rows):
    latencies = [row["latency_ms"] for row in rows]
    return {
        "cases": len(rows),
        "hit_rate": sum(row["source_hit"] for row in rows) / max(1, len(rows)),
        "guardrail_precision": sum(row["guardrail_hit"] for row in rows) / max(1, len(rows)),
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0,
    }

# %% [markdown]
# ## 5. Run Experiments

# %%
def run_experiment(name, fn):
    rows = []
    for case in golden_cases:
        started = time.perf_counter()
        result = fn(case["user_question"])
        result.setdefault("latency_ms", (time.perf_counter() - started) * 1000)
        rows.append(score_case(case, result))
    return rows

# Uncomment when implementations are wired.
# all_results = {name: run_experiment(name, fn) for name, fn in EXPERIMENTS.items()}
# summaries = {name: summarize_scores(rows) for name, rows in all_results.items()}
# summaries

# %% [markdown]
# ## 6. Session Memory Isolation
#
# Required checks:
#
# 1. Open table session T01.
# 2. Send chat: "Tôi dị ứng hải sản".
# 3. Refresh page and ask: "Vậy tôi nên tránh món nào?"
# 4. Expected: AI remembers seafood allergy inside the same table session.
# 5. Close table session.
# 6. Open a new T01 session.
# 7. Ask: "Tôi có dị ứng gì không?"
# 8. Expected: AI must not remember the previous guest.

# %% [markdown]
# ## 7. Decision Log
#
# Fill this only after metrics exist:
#
# | Date | Dataset | Best config | Why | Risks | Production decision |
# |---|---|---|---|---|---|
# | TBD | golden_questions.csv | TBD | TBD | TBD | TBD |

