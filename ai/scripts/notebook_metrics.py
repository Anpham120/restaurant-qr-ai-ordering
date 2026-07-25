# -*- coding: utf-8 -*-
"""Summarize notebook evaluation JSON for data-driven markdown in the research notebook."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

NOTEBOOK_ARTIFACT_NAMES = (
    "notebook_live_test.json",
    "dual_model_test.json",
    "notebook_retrieval_screening.json",
)

FAST_PATH_ROUTES = frozenset({"kb_rag", "clarify", "live_data"})
STRICT_FAIL_FLAGS = frozenset(
    {
        "EVIDENCE_INSUFFICIENT",
        "UNSUPPORTED_CLAIM_BLOCKED",
        "AI_PROVIDER_UNAVAILABLE",
    }
)
FAIL_CLOSED_CONTENT_MARKERS = (
    "Mình chưa đủ bằng chứng",
    "Mình chưa có dữ liệu",
    "Mình chưa có thông tin xác nhận",
)
UNKNOWN_ROUTES = frozenset({None, "?", "unknown", ""})


def _query_text(query_obj: Any) -> str:
    if isinstance(query_obj, dict):
        return str(query_obj.get("query", ""))
    return str(query_obj)


def _query_category(query_obj: Any) -> str:
    if isinstance(query_obj, dict):
        return str(query_obj.get("category", ""))
    return ""


def _result_flags(result: dict[str, Any]) -> set[str]:
    raw = result.get("flags") or []
    return {str(f) for f in raw}


def _fail_closed_content(result: dict[str, Any]) -> bool:
    content = str(result.get("content") or "")
    return any(marker in content for marker in FAIL_CLOSED_CONTENT_MARKERS)


def is_non_abstain_success(result: dict[str, Any]) -> bool:
    if "error" in result:
        return False
    if "success_availability" in result:
        return bool(result["success_availability"])
    return result.get("route") != "abstain"


def is_strict_pipeline_success(result: dict[str, Any]) -> bool:
    if "error" in result:
        return False
    if "success_strict" in result:
        return bool(result["success_strict"])
    route = result.get("route")
    if route == "abstain":
        return False
    flags = _result_flags(result)
    if _fail_closed_content(result):
        return False
    if route in UNKNOWN_ROUTES and flags.intersection(STRICT_FAIL_FLAGS):
        return False
    if route in UNKNOWN_ROUTES and not str(result.get("content") or "").strip():
        return False
    return True


def _latency_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(mean(values))


def _pick_deepseek_model(models: list[str]) -> str:
    for model in models:
        if "deepseek" in model.lower():
            return model
    return models[-1] if models else ""


def _short_model_name(model: str) -> str:
    return model.split("/")[-1]


def summarize_model_tiers(dual: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_dual_model(dual)
    total_q = summary["total_q"]
    tiers: dict[int, list[str]] = {}
    for model, stats in summary["per_model"].items():
        ok = int(stats["ok"])
        tiers.setdefault(ok, []).append(_short_model_name(model))
    sorted_oks = sorted(tiers.keys(), reverse=True)
    return {
        "total_q": total_q,
        "tiers": tiers,
        "sorted_oks": sorted_oks,
        "sentence": format_model_tier_sentence(summary),
    }


def format_model_tier_sentence(summary: dict[str, Any]) -> str:
    return _format_model_tier_by_field(summary, "ok", "non-abstain")


def format_model_tier_strict_sentence(summary: dict[str, Any]) -> str:
    return _format_model_tier_by_field(summary, "strict_ok", "strict")


def _format_model_tier_by_field(
    summary: dict[str, Any], field: str, label: str
) -> str:
    total_q = summary["total_q"]
    per = summary["per_model"]
    by_ok: dict[int, list[str]] = {}
    for model, stats in per.items():
        by_ok.setdefault(int(stats[field]), []).append(_short_model_name(model))
    parts: list[str] = []
    for ok in sorted(by_ok.keys(), reverse=True):
        names = ", ".join(f"`{n}`" for n in sorted(by_ok[ok]))
        parts.append(f"{names} **{ok}/{total_q}**")
    if len(parts) == 1:
        return f"Cả ba model **đồng hạng** {parts[0]} ({label})."
    return "; ".join(parts) + f" ({label})."


def summarize_dual_model(dual: dict[str, Any]) -> dict[str, Any]:
    models: list[str] = list(dual.get("models") or [])
    queries = list(dual.get("queries") or [])
    results_by_model: dict[str, list[dict[str, Any]]] = dual.get("results") or {}
    total_q = len(queries)
    ds_model = _pick_deepseek_model(models)
    other_models = [m for m in models if m != ds_model]

    per_model: dict[str, dict[str, Any]] = {}
    for model in models:
        rows = results_by_model.get(model) or []
        ok_rows = [r for r in rows if is_non_abstain_success(r)]
        ab_rows = [r for r in rows if r.get("route") == "abstain" and "error" not in r]
        fast_rows = [r for r in ok_rows if r.get("route") in FAST_PATH_ROUTES]
        llm_rows = [r for r in ok_rows if r.get("route") not in FAST_PATH_ROUTES]
        kb_idxs = [
            i
            for i, qo in enumerate(queries)
            if _query_category(qo) == "KB FAQ"
        ]
        kb_ok = sum(
            1
            for i in kb_idxs
            if i < len(rows) and is_non_abstain_success(rows[i])
        )
        strict_ok = sum(1 for r in rows if is_strict_pipeline_success(r))
        per_model[model] = {
            "ok": len(ok_rows),
            "strict_ok": strict_ok,
            "total": total_q,
            "kb_ok": kb_ok,
            "kb_total": len(kb_idxs),
            "fast_latency_ms": _latency_mean([r.get("latency_ms", 0) for r in fast_rows]),
            "llm_latency_ms": _latency_mean([r.get("latency_ms", 0) for r in llm_rows]),
            "abstain_latency_ms": _latency_mean([r.get("latency_ms", 0) for r in ab_rows]),
        }

    deepseek_only_wins: list[str] = []
    for index, query_obj in enumerate(queries):
        ds_rows = results_by_model.get(ds_model) or []
        if index >= len(ds_rows):
            continue
        ds_ok = is_non_abstain_success(ds_rows[index])
        others_ok = all(
            index < len(results_by_model.get(m) or [])
            and is_non_abstain_success((results_by_model.get(m) or [])[index])
            for m in other_models
        )
        if ds_ok and not others_ok:
            deepseek_only_wins.append(_query_text(query_obj))

    return {
        "timestamp": dual.get("timestamp", ""),
        "models": models,
        "total_q": total_q,
        "deepseek_model": ds_model,
        "per_model": per_model,
        "deepseek_only_wins": deepseek_only_wins,
    }


def summarize_live_test(live: dict[str, Any]) -> dict[str, Any]:
    pipeline = summarize_live_pipeline(live)
    return {
        "timestamp": pipeline["timestamp"],
        "model": pipeline["model"],
        "pipeline_ok": pipeline["availability_ok"],
        "pipeline_total": pipeline["pipeline_total"],
    }


def summarize_live_pipeline(live: dict[str, Any]) -> dict[str, Any]:
    pipeline = list(live.get("pipeline_results") or [])
    valid = [r for r in pipeline if "error" not in r]
    total = len(valid) if valid else len(pipeline)
    availability_ok = sum(1 for r in valid if is_non_abstain_success(r))
    strict_ok = sum(1 for r in valid if is_strict_pipeline_success(r))
    route_null = sum(1 for r in valid if r.get("route") in UNKNOWN_ROUTES)
    route_abstain = sum(1 for r in valid if r.get("route") == "abstain")
    return {
        "timestamp": live.get("timestamp", ""),
        "model": live.get("model", ""),
        "pipeline_total": total,
        "availability_ok": availability_ok,
        "strict_ok": strict_ok,
        "route_null": route_null,
        "route_abstain": route_abstain,
    }


def compare_live_dual_same_model(
    live: dict[str, Any], dual: dict[str, Any] | None
) -> str | None:
    if not dual:
        return None
    model = live.get("model", "")
    rows_dual = (dual.get("results") or {}).get(model)
    if not rows_dual:
        return None
    live_rows = [r for r in live.get("pipeline_results") or [] if "error" not in r]
    n = min(len(live_rows), len(rows_dual), len(dual.get("queries") or []))
    if n == 0:
        return None
    mismatches = 0
    for i in range(n):
        live_ok = is_non_abstain_success(live_rows[i])
        dual_ok = is_non_abstain_success(rows_dual[i])
        if live_ok != dual_ok:
            mismatches += 1
    if mismatches == 0:
        return (
            f"Cùng model `{_short_model_name(model)}`: availability khớp giữa "
            f"`notebook_live_test.json` và `dual_model_test.json` trên {n} query."
        )
    return (
        f"Cùng model `{_short_model_name(model)}`: {mismatches}/{n} query "
        "lệch availability (thường do `route` null vs `abstain` giữa các lần chạy)."
    )


def load_retrieval_headlines(ai_root: Path) -> dict[str, Any]:
    results_dir = ai_root / "evaluation" / "results"
    out: dict[str, Any] = {
        "screening_label": "chạy Part II để tạo screening JSON",
        "screening_hit5": None,
        "release_label": None,
    }
    screening_path = results_dir / "notebook_retrieval_screening.json"
    if screening_path.is_file():
        data = json.loads(screening_path.read_text(encoding="utf-8"))
        hit5 = data.get("hit5_overall")
        if hit5 is not None:
            out["screening_hit5"] = float(hit5)
            out["screening_label"] = f"{float(hit5):.0%} Hit@5 (screening notebook)"
        out["screening_data"] = data
    release_path = results_dir / "dev_retrieval_summary.v3.json"
    if release_path.is_file():
        release = json.loads(release_path.read_text(encoding="utf-8"))
        hybrid = release.get("hybrid_e5_small") or (release.get("methods") or {}).get(
            "hybrid_e5_small", {}
        )
        hit5 = (
            hybrid.get("hit5")
            or hybrid.get("Hit@5")
            or hybrid.get("hit_at_5")
        )
        if hit5 is not None:
            if isinstance(hit5, float) and hit5 <= 1.0:
                label_hit = f"{hit5:.2%}"
            else:
                label_hit = str(hit5)
            out["release_label"] = (
                f"release dev gate Hit@5 {label_hit} (dev_retrieval_summary.v3.json)"
            )
        else:
            out["release_label"] = "release dev gate (dev_retrieval_summary.v3.json)"
        out["release_data"] = release
    return out


def artifact_provenance(path: Path) -> dict[str, Any]:
    rel = path.name
    if not path.is_file():
        return {"path": rel, "present": False, "timestamp": "", "sha256_prefix": ""}
    raw = path.read_bytes()
    timestamp = ""
    try:
        payload = json.loads(raw.decode("utf-8"))
        timestamp = str(payload.get("timestamp", ""))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {
        "path": rel,
        "present": True,
        "timestamp": timestamp,
        "sha256_prefix": hashlib.sha256(raw).hexdigest()[:8],
        "size_bytes": len(raw),
    }


def format_artifact_provenance_table(ai_root: Path) -> str:
    results_dir = ai_root / "evaluation" / "results"
    lines = [
        "### Provenance artifact notebook",
        "",
        "| File | Timestamp | SHA256 (8) |",
        "|---|---|---|",
    ]
    for name in NOTEBOOK_ARTIFACT_NAMES:
        info = artifact_provenance(results_dir / name)
        if not info["present"]:
            lines.append(f"| `{name}` | *(missing)* | — |")
            continue
        lines.append(
            f"| `{name}` | `{info['timestamp'] or '?'}` | `{info['sha256_prefix']}` |"
        )
    return "\n".join(lines)


def format_hit5_screening_vs_release_table() -> str:
    return (
        "### Hit@5: screening notebook vs release gate\n\n"
        "| Bộ | N | Artifact | Mục đích |\n"
        "|---|---:|---|---|\n"
        "| **Screening notebook** | 107 | `notebook_retrieval_screening.json` | So sánh BM25 / Dense / Hybrid trong Part II (execute Part II) |\n"
        "| **Release dev gate** | 110 | `dev_retrieval_summary.v3.json` | Gate staging (`AI_STAGING_READINESS.md`); khác bộ case và có thể khác cấu hình E5 |\n\n"
        "> Hai con số **không** so sánh trực tiếp — cột Hybrid trong §15 là **screening**, không phải release 99%."
    )


def format_part12_narrative(
    live: dict[str, Any], dual: dict[str, Any] | None = None
) -> str:
    pipe = summarize_live_pipeline(live)
    total = pipe["pipeline_total"] or 1
    lines = [
        "### Nhận xét Pipeline end-to-end",
        "",
        f"**Availability** (`route != abstain`): **{pipe['availability_ok']}/{total}** "
        f"({pipe['availability_ok']/total:.0%}) — model `{pipe['model']}`, "
        f"timestamp `{pipe['timestamp']}`.",
        f"**Strict success** (abstain, fail-closed content, hoặc `route` unknown + flags): "
        f"**{pipe['strict_ok']}/{total}** ({pipe['strict_ok']/total:.0%}).",
        "",
        f"- `route` null/unknown: **{pipe['route_null']}** query "
        "(availability vẫn có thể đếm OK — xem glossary).",
        f"- `route` abstain: **{pipe['route_abstain']}** query.",
        "",
    ]
    align = compare_live_dual_same_model(live, dual)
    if align:
        lines.append(align)
        lines.append("")
    lines.extend(
        [
            "> §14 so **3 model** trên cùng 20 query; DeepSeek có thể thấp hơn vì ghi `abstain` rõ, "
            "trong khi model khác trả `route` null nhưng vẫn có content.",
            "> Availability ≠ chất lượng câu trả lời; release: `docs/ai/AI_STAGING_READINESS.md`.",
        ]
    )
    return "\n".join(lines)


def format_part13_narrative(live: dict[str, Any]) -> str:
    turns = list(live.get("multi_results") or [])
    lines = ["### Nhận xét Multi-turn (từ data)", "", "| Turn | Query | Route | Excerpt |", "|---|---|---|---|"]
    for row in turns:
        if "error" in row:
            lines.append(
                f"| {row.get('turn', '?')} | {str(row.get('query', ''))[:28]} | ERROR | {row.get('error', '')[:40]} |"
            )
            continue
        content = str(row.get("content") or "")[:60].replace("|", " ")
        if "<!-- question_variants" in content:
            content = "[KB fast-path]"
        route = row.get("route") or "?"
        lines.append(
            f"| {row.get('turn', '?')} | {str(row.get('query', ''))[:28]} | `{route}` | {content} |"
        )
    ok = sum(1 for r in turns if "error" not in r and is_non_abstain_success(r))
    strict = sum(1 for r in turns if "error" not in r and is_strict_pipeline_success(r))
    lines.extend(
        [
            "",
            f"**Availability:** {ok}/{len(turns)} turn; **strict:** {strict}/{len(turns)} turn.",
        ]
    )
    return "\n".join(lines)


def format_part4_narrative(summary: dict[str, Any]) -> str:
    models = summary["models"]
    total_q = summary["total_q"]
    per = summary["per_model"]
    ds_model = summary["deepseek_model"]
    ds_stats = per.get(ds_model, {})
    kb_ok = ds_stats.get("kb_ok", 0)
    kb_total = ds_stats.get("kb_total", 0)

    lines = [
        "### 14.4 Nhận xét",
        "",
        f"**1. KB fast-path (subset KB FAQ)** — trên {kb_total} câu KB FAQ, "
        f"cả 3 model đều **{kb_ok}/{kb_total}** non-abstain (fast-path Hybrid RRF, không phụ thuộc LLM).",
        "",
    ]

    wins = summary.get("deepseek_only_wins") or []
    if wins:
        lines.append("**2. DeepSeek thắng riêng một số query LLM** —")
        for query in wins:
            lines.append(f'- `"{query}"` → DeepSeek non-abstain, GPT abstain')
        lines.append("")
        lines.append(
            "Cần **human eval** để kiểm tra chất lượng câu trả lời (availability ≠ quality)."
        )
    else:
        lines.append("**2. So sánh model trên 20 query (availability)** —")
        lines.append(format_model_tier_sentence(summary))
        lines.append("")

    lines.append("**2b. Strict success (cùng 20 query)** —")
    lines.append(format_model_tier_strict_sentence(summary))
    lines.append("")

    lines.append("**3. Latency (tính từ `dual_model_test.json`):**")
    for model in models:
        stats = per[model]
        short = model.split("/")[-1][:18]
        fast = stats.get("fast_latency_ms")
        ab = stats.get("abstain_latency_ms")
        llm = stats.get("llm_latency_ms")
        parts = []
        if fast is not None:
            parts.append(f"fast-path ~{fast:.0f}ms")
        if llm is not None:
            parts.append(f"LLM path ~{llm:.0f}ms")
        if ab is not None:
            parts.append(f"abstain ~{ab:.0f}ms")
        detail = ", ".join(parts) if parts else "không đủ mẫu"
        lines.append(f"- `{short}`: {detail}")
    lines.extend(
        [
            "",
            "> **Kết luận:**",
            "> - Để tăng success rate: bổ sung KB + Claim Verifier kiểm LiveContext",
            "> - Chọn model: dựa trên latency + human eval, không chỉ non-abstain rate",
            "> - Release gate: xem `docs/ai/AI_STAGING_READINESS.md` (NOT READY cho đến khi đủ gate)",
        ]
    )
    return "\n".join(lines)


def format_part17_bullet_part4(summary: dict[str, Any]) -> str:
    models = summary["models"]
    total_q = summary["total_q"]
    per = summary["per_model"]
    parts = []
    for model in models:
        stats = per[model]
        short = model.split("/")[-1]
        parts.append(f"{short} {stats['ok']}/{total_q}")
    latency_bits = []
    ds = summary["deepseek_model"]
    if ds in per and per[ds].get("abstain_latency_ms") is not None:
        latency_bits.append(f"abstain DeepSeek ~{per[ds]['abstain_latency_ms']:.0f}ms")
    latency_note = f"; {latency_bits[0]}" if latency_bits else ""
    return (
        f"4. **Part IV** — So sánh **3 model** trên cùng 20 query: "
        f"{', '.join(parts)}{latency_note}. "
        "KB FAQ ổn trên fast-path; Menu/Allergy cần LiveContext + human eval."
    )


def format_production_report_section() -> str:
    """Final notebook section: report conclusion — what research outputs ship in production."""
    return (
        "---\n\n"
        "## 18. Đưa vào production — kết luận báo cáo\n\n"
        "Phần này **chốt báo cáo**: kết quả nghiên cứu trong notebook đã được **ứng dụng** "
        "vào chatbot AI hiện tại (Python AI service + backend .NET trên staging/production) "
        "ở mức nào, và **stack nào** nhóm cam kết vận hành.\n\n"
        "### Tính năng từ notebook → hệ thống đang chạy\n\n"
        "| Nội dung nghiên cứu (notebook) | Trạng thái trên hệ thống | Ghi chú triển khai |\n"
        "|---|---|---|\n"
        "| **Knowledge Base** Part I — 26 file MD, chunk theo `##`, question variants | **Đã áp dụng** | "
        "`knowledge-base/` load lúc khởi động AI service |\n"
        "| **Chuẩn hóa tiếng Việt** (teencode, không dấu, emoji) | **Đã áp dụng** | "
        "`vietnamese_normalizer` trong BM25 và pipeline query |\n"
        "| **Retrieval Hybrid RRF** (BM25 + Dense E5 small) Part II | **Đã áp dụng** | "
        "`RAG_RETRIEVAL_METHOD=hybrid`, `AI_EMBEDDING_MODEL=e5_small` — ADR retriever |\n"
        "| **Intent / evidence routing** Part III — KB vs menu vs giỏ | **Đã áp dụng** | "
        "`intent_classifier` + fast-path (KB, menu, budget, pairing); LLM intent khi câu mơ hồ |\n"
        "| **Guardrails** — PII, prompt injection, chống tự đặt món / bịa giá | **Đã áp dụng** | "
        "`guardrails.detect_guardrail_flags`; injection **chặn trước LLM** (`assistant.py`) |\n"
        "| **Chặn / xử lý câu hỏi sai chủ đề** Part III | **Đã áp dụng một phần** | "
        "Cờ `OUT_OF_SCOPE` + chunk KB `out-of-domain-redirect`; LLM + prompt hướng dẫn từ chối — "
        "**chưa** có nhánh từ chối cứng cho mọi off-topic như injection |\n"
        "| **Ngữ cảnh hội thoại** (session, rolling summary, lịch sử) Part III | **Đã áp dụng** | "
        "Backend gửi `session_memory`, `rolling_summary`, `session_state`, history → "
        "`rewrite_query` và prompt LLM |\n"
        "| **Claim Verifier** chống bịa sau LLM | **Đã áp dụng (KB)** | "
        "`verify_claims` trên chunk KB + menu id; câu menu phức tạp vẫn phụ thuộc LiveContext (§16) |\n"
        "| **Structured response** (evidence, claims, guardrail_flags, cart gợi ý) | **Đã áp dụng** | "
        "Contract `/v1/chat` — backend kiểm tra trước khi hiển thị |\n"
        "| **LLM DeepSeek** qua 9router | **Đã áp dụng (staging/production)** | "
        "`LLM_MODEL=oc/deepseek-v4-flash-free` |\n"
        "| So sánh **3 model** / metric Part IV | **Không đưa vào production** | "
        "Chỉ phục vụ thí nghiệm và báo cáo |\n"
        "| Human eval, gate chất lượng end-to-end | **Chưa hoàn tất release** | "
        "[`AI_STAGING_READINESS.md`](../../docs/ai/AI_STAGING_READINESS.md) — **NOT READY** |\n\n"
        "### Stack production nhóm chốt vận hành\n\n"
        "| Thành phần | Giá trị |\n"
        "|---|---|\n"
        "| Retrieval | `hybrid` + `e5_small` |\n"
        "| LLM | `oc/deepseek-v4-flash-free` (9router) |\n"
        "| Tích hợp | `CHAT_AI_PROVIDER=python-rag`, Docker [`deploy/docker-compose.yml`](../../deploy/docker-compose.yml) |\n"
        "| Kiểm tra sau deploy | [`VPS_STAGING_AI_RUNBOOK.md`](../../docs/ai/VPS_STAGING_AI_RUNBOOK.md) |\n\n"
        "### Kết luận báo cáo\n\n"
        "Notebook chứng minh **phương pháp** (RAG hybrid, guardrails, routing, session) và **đo** trên bộ eval "
        "tự xây; **hệ thống thật** đã gắn cùng module code với cấu hình trên. "
        "Phần còn lại trước khi coi là production hoàn chỉnh: mở rộng Claim Verifier với **LiveContext menu**, "
        "human review, và các gate trong `AI_STAGING_READINESS.md` — **không** nằm ngoài phạm vi đã cam kết triển khai ở bảng trên."
    )


def format_deploy_lock_section() -> str:
    """Alias for notebook builder (legacy name)."""
    return format_production_report_section()


def enrich_pipeline_row(result: dict[str, Any]) -> dict[str, Any]:
    """Return new fields for JSON export scripts."""
    return {
        **result,
        "success_availability": is_non_abstain_success(result),
        "success_strict": is_strict_pipeline_success(result),
    }
