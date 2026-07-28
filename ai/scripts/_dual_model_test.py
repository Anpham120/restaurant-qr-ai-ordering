# -*- coding: utf-8 -*-
"""Compare cx/gpt-5.5 vs cx/gpt-5.6-luna-review — 20 queries, comprehensive eval."""
import asyncio, json, sys, os, time
from pathlib import Path
sys.path.insert(0, '.')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.chdir(str(Path(__file__).resolve().parents[1]))

import app.config as app_cfg
app_cfg.is_supported_router_model = lambda m: True

from app.config import load_config, AiServiceConfig
from app.services.assistant import AiAssistantService
from scripts.notebook_metrics import enrich_pipeline_row

# 20 queries, 6 categories — THỐNG NHẤT với _run_live_tests.py
queries = [
    # KB FAQ — restaurant info (7)
    ("nhà hàng có wifi không?", "KB FAQ"),
    ("mật khẩu wifi là gì?", "KB FAQ"),
    ("có chỗ đậu xe không?", "KB FAQ"),
    ("giờ mở cửa là mấy giờ?", "KB FAQ"),
    ("thanh toán bằng thẻ được không?", "KB FAQ"),
    ("nhà hàng có phòng riêng không?", "KB FAQ"),
    ("chính sách hủy đơn thế nào?", "KB FAQ"),
    # Menu / Recommendation (5)
    ("có món nào không cay không?", "Menu"),
    ("gợi ý món ngon đi", "Menu"),
    ("phở bò bao nhiêu tiền?", "Menu"),
    ("có món chay không?", "Menu"),
    ("combo cho 4 người?", "Menu"),
    # Allergy / Safety (3)
    ("tôi dị ứng tôm", "Allergy"),
    ("có món nào không có đậu phộng?", "Allergy"),
    ("món nào ăn được cho người tiểu đường?", "Allergy"),
    # Order (2)
    ("đặt 2 phần phở bò", "Order"),
    ("thêm 1 trà đá", "Order"),
    # Off-topic (2)
    ("thời tiết hôm nay?", "Off-topic"),
    ("bitcoin giá bao nhiêu?", "Off-topic"),
    # Chitchat (1)
    ("cảm ơn nhé", "Chitchat"),
]

# DeepSeek dropped: the 9router route serving oc/deepseek-v4-flash-free in this
# account rejects response_format=json_object (see docs/ai/AI_DECISION_HISTORY.md).
# cx/gpt-5.6-luna-review is now the configured runtime primary (app/config.py).
models = ["cx/gpt-5.5", "cx/gpt-5.6-luna-review"]
all_results = {}

for model_name in models:
    print(f"\n{'='*60}")
    print(f"MODEL: {model_name}")
    print(f"{'='*60}")

    base_cfg = load_config()
    cfg = AiServiceConfig(
        provider=base_cfg.provider, base_url=base_cfg.base_url,
        api_key=base_cfg.api_key, model=model_name,
        llm_timeout_seconds=base_cfg.llm_timeout_seconds,
        request_budget_seconds=base_cfg.request_budget_seconds,
        max_retry=base_cfg.max_retry, max_tokens=base_cfg.max_tokens,
        reasoning_effort=base_cfg.reasoning_effort,
        knowledge_base_path=base_cfg.knowledge_base_path,
        top_k=base_cfg.top_k, retrieval_method=base_cfg.retrieval_method,
        embedding_model=base_cfg.embedding_model,
    )

    svc = AiAssistantService(cfg)
    svc.prewarm()

    model_results = []
    for q, cat in queries:
        t0 = time.perf_counter()
        try:
            resp = asyncio.get_event_loop().run_until_complete(svc.chat({
                "message": q,
                "history": [],
                "session_state": {},
                "live_context": {"menu_items": [
                    {"id": "pho-bo", "name": "Phở bò", "price": 55000, "category": "Món chính", "description": "Phở bò truyền thống, nước dùng hầm xương 12h", "allergens": [], "spicy": False},
                    {"id": "pho-ga", "name": "Phở gà", "price": 50000, "category": "Món chính", "description": "Phở gà ta, thịt gà thả vườn", "allergens": [], "spicy": False},
                    {"id": "bun-bo-hue", "name": "Bún bò Huế", "price": 60000, "category": "Món chính", "description": "Bún bò cay nồng đặc trưng Huế", "allergens": ["tôm"], "spicy": True},
                    {"id": "com-tam", "name": "Cơm tấm sườn", "price": 45000, "category": "Món chính", "description": "Cơm tấm sườn nướng, bì, chả", "allergens": [], "spicy": False},
                    {"id": "goi-cuon", "name": "Gỏi cuốn tôm thịt", "price": 35000, "category": "Khai vị", "description": "Gỏi cuốn tươi với tôm và thịt heo", "allergens": ["tôm"], "spicy": False},
                    {"id": "cha-gio", "name": "Chả giò", "price": 30000, "category": "Khai vị", "description": "Chả giò giòn rụm", "allergens": [], "spicy": False},
                    {"id": "canh-chua", "name": "Canh chua cá", "price": 65000, "category": "Món chính", "description": "Canh chua cá lóc miền Tây", "allergens": [], "spicy": False},
                    {"id": "ga-nuong", "name": "Gà nướng mật ong", "price": 120000, "category": "Món chính", "description": "Gà ta nướng mật ong, da giòn", "allergens": ["đậu phộng"], "spicy": False},
                    {"id": "rau-muong", "name": "Rau muống xào tỏi", "price": 25000, "category": "Rau", "description": "Rau muống xào tỏi giòn", "allergens": [], "spicy": False},
                    {"id": "dau-hu", "name": "Đậu hũ sốt cà", "price": 30000, "category": "Chay", "description": "Đậu hũ non sốt cà chua", "allergens": [], "spicy": False},
                    {"id": "com-chay", "name": "Cơm chiên chay", "price": 40000, "category": "Chay", "description": "Cơm chiên rau củ", "allergens": [], "spicy": False},
                    {"id": "tra-da", "name": "Trà đá", "price": 5000, "category": "Đồ uống", "description": "Trà đá mát lạnh", "allergens": [], "spicy": False},
                    {"id": "nuoc-chanh", "name": "Nước chanh", "price": 15000, "category": "Đồ uống", "description": "Nước chanh tươi", "allergens": [], "spicy": False},
                    {"id": "combo-4", "name": "Combo gia đình 4 người", "price": 250000, "category": "Combo", "description": "Phở bò x2 + Gỏi cuốn + Chả giò + 4 Trà đá", "allergens": ["tôm"], "spicy": False},
                ]},
            }))
            elapsed = (time.perf_counter() - t0) * 1000
            decision = resp.get("decision", {})
            content = (resp.get("content", "") or "")[:200]
            latency = resp.get("latency_ms", {})

            result = enrich_pipeline_row({
                "query": q, "category": cat,
                "route": decision.get("route", "?"),
                "intent": decision.get("intent", "?"),
                "content": content,
                "latency_ms": round(latency.get("total", elapsed), 1),
                "path": latency.get("path", "?"),
                "flags": resp.get("guardrail_flags", []),
                "evidence_count": len(resp.get("evidence", [])),
                "content_length": len(content),
            })
            model_results.append(result)
            status = "OK" if decision.get("route") not in ("abstain",) else "ABSTAIN"
            print(f"  [{cat:9s}] {q[:32]:32s} {status:8s} {elapsed:7.0f}ms [{decision.get('route','?')}]")
        except Exception as e:
            model_results.append({"query": q, "category": cat, "error": str(e)[:100]})
            print(f"  [{cat:9s}] {q[:32]:32s} ERROR")

    all_results[model_name] = model_results
    ok = len([r for r in model_results if r.get("route") not in ("abstain",) and "error" not in r])
    print(f"\n  Summary: {ok}/{len(queries)} OK")

# Save
out = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "models": models,
    "queries": [{"query": q, "category": c} for q, c in queries],
    "results": all_results,
}
out_path = Path("evaluation/results/dual_model_test.json")
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {out_path}")
