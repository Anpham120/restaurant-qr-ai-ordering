from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "notebooks" / "academic_retrieval_study.ipynb"


def main() -> None:
    cells = [
        _markdown(
            """
            # Nghiên cứu RAG cho chatbot CMC Restaurant

            Notebook này mô tả một quy trình nghiên cứu có thể tái lập theo thứ tự:
            dữ liệu → document hóa → tiền xử lý → các phương án retrieval → tuning trên
            development set → frozen test → quyết định production → demo chatbot RAG.

            Đây là notebook thực thi được, không phải báo cáo chèn sẵn kết quả. Mọi metric chỉ
            được đọc sau khi checksum của artifact khớp code và dữ liệu hiện tại.
            """
        ),
        _markdown(
            """
            ## 0. Bài toán và câu hỏi nghiên cứu

            Khách quét QR cần hỏi về menu, giá, món còn phục vụ và chính sách. Chatbot chỉ tư
            vấn dựa trên evidence kiểm soát; không tự tạo đơn, sửa giỏ hoặc thanh toán.

            Không có bước fine-tune trong scope hiện tại. Tương đương với huấn luyện trong
            ML/DL ở đây là xây index, chọn representation và tune siêu tham số retriever.

            - RQ1: TF-IDF, BM25, dense embedding hay hybrid RRF xếp hạng tốt nhất?
            - RQ2: Phương án nào bền vững với tiếng Việt không dấu, paraphrase, policy và
              multi-intent?
            - RQ3: Phương án nào cân bằng chất lượng, độ trễ và chi phí vận hành?
            - RQ4: Câu trả lời cuối có grounded, an toàn và truy vết được nguồn không?
            """
        ),
        _code(
            """
            from __future__ import annotations

            import hashlib
            import json
            import os
            import subprocess
            import sys
            from pathlib import Path

            import matplotlib.pyplot as plt
            import pandas as pd
            from IPython.display import Markdown, display


            def locate_ai_root() -> Path:
                cwd = Path.cwd().resolve()
                candidates = [cwd, *cwd.parents, cwd / "ai"]
                for candidate in candidates:
                    if (candidate / "app").is_dir() and (candidate / "research").is_dir():
                        return candidate
                raise RuntimeError(
                    "Không tìm thấy thư mục ai/. Mở notebook từ repository hoặc ai/notebooks."
                )


            AI_ROOT = locate_ai_root()
            PROJECT_ROOT = AI_ROOT.parent
            RESEARCH = AI_ROOT / "research"
            ARTIFACTS = RESEARCH / "artifacts"
            DATA = AI_ROOT / "data"

            if str(AI_ROOT) not in sys.path:
                sys.path.insert(0, str(AI_ROOT))

            RUN_PIPELINE = False
            RUN_LIVE_SERVICE_DEMO = False
            AI_SERVICE_URL = "http://127.0.0.1:8001"

            print(f"AI root: {AI_ROOT}")
            print("Chế độ an toàn: không tái tạo artifact và không gọi LLM mặc định.")
            """,
            tags=["parameters"],
        ),
        _markdown(
            """
            ## 1. Provenance và cổng tái lập

            Artifact là evidence chỉ khi nó được tạo từ đúng dữ liệu, script và cấu hình hiện
            tại. Nếu có checksum không khớp, notebook hiển thị BLOCK và không diễn giải metric
            hay dùng kết quả để chọn production.
            """
        ),
        _code(
            """
            def sha256(path: Path) -> str | None:
                if not path.exists():
                    return None
                return hashlib.sha256(path.read_bytes()).hexdigest()


            def refresh_provenance():
                environment_path = ARTIFACTS / "environment.json"
                environment = (
                    json.loads(environment_path.read_text(encoding="utf-8"))
                    if environment_path.exists()
                    else {}
                )
                targets = {
                    "queries": ("queries_sha256", RESEARCH / "queries.csv"),
                    "menu_snapshot": ("menu_snapshot_sha256", RESEARCH / "menu_snapshot.json"),
                    "policies": ("policy_sha256", DATA / "policies.json"),
                    "evaluation_script": ("evaluation_script_sha256", RESEARCH / "run_experiments.py"),
                }
                rows = []
                for name, (key, path) in targets.items():
                    recorded = environment.get(key)
                    actual = sha256(path)
                    rows.append(
                        {
                            "component": name,
                            "path": str(path.relative_to(PROJECT_ROOT)),
                            "fresh": bool(recorded and actual and recorded == actual),
                            "recorded_sha256": recorded,
                            "current_sha256": actual,
                        }
                    )
                frame = pd.DataFrame(rows)
                return environment, frame, bool(not frame.empty and frame["fresh"].all())


            artifact_environment, provenance_frame, ARTIFACTS_FRESH = refresh_provenance()
            display(provenance_frame)
            message = "**PASS:** artifact khớp code và dữ liệu." if ARTIFACTS_FRESH else (
                "**BLOCK:** artifact chưa khớp code hoặc dữ liệu. Chạy lại pipeline ở mục 6."
            )
            display(Markdown(message))
            """
        ),
        _markdown(
            """
            ## 2. Chuẩn bị dữ liệu và khám phá dữ liệu

            Menu chuẩn được đọc từ seed backend; policy được version trong JSON. Benchmark gồm
            query template có kiểm soát và ca gán nhãn thủ công: semantic paraphrase, policy,
            multi-intent và hard-negative. Variants của cùng menu item hoặc policy phải ở cùng
            một split để tránh leakage.
            """
        ),
        _code(
            """
            from research.build_dataset import DEFAULT_SEED, build_cases

            cases, snapshot = build_cases(DEFAULT_SEED, RESEARCH / "manual_cases.json")
            case_frame = pd.DataFrame(cases)
            menu_frame = pd.DataFrame(
                [
                    {
                        "id": item.id,
                        "category": item.category_name,
                        "name": item.name,
                        "description_length": len(item.description or ""),
                    }
                    for item in snapshot.items
                ]
            )

            print(f"Menu: {len(menu_frame)} món | {menu_frame['category'].nunique()} danh mục")
            print(f"Queries: {len(case_frame)}")
            display(case_frame.groupby(["split", "slice"]).size().rename("queries").reset_index())
            display(menu_frame.groupby("category").size().rename("menu_items").sort_values(ascending=False))
            """
        ),
        _code(
            """
            generated_slices = {"exact_name", "no_diacritic", "category_intent"}
            generated_share = case_frame["slice"].isin(generated_slices).mean()
            print(f"Tỷ lệ query sinh theo menu/template: {generated_share:.1%}")

            query_lengths = case_frame.assign(tokens=case_frame["question"].str.split().str.len())
            display(query_lengths.groupby("slice")["tokens"].agg(["count", "mean", "min", "max"]).round(2))
            display(case_frame.sample(min(8, len(case_frame)), random_state=42))

            print(
                "Báo cáo phải nêu rõ tỷ lệ query template và query giống người dùng để tránh "
                "đánh giá quá cao lexical retrieval."
            )
            """
        ),
        _markdown(
            """
            ## 3. Document hóa, tiền xử lý và chunking

            Mỗi món là một document nguyên tử gồm tên, danh mục, mô tả và tags; mỗi policy là
            một document có answer và aliases. Không chunking menu vì một món ngắn là đơn vị
            nghiệp vụ nguyên tử: chia nhỏ sẽ làm mất liên kết an toàn giữa menu ID, giá và
            availability. Đây là quyết định thiết kế được giải thích, không phải bước bị bỏ qua.
            """
        ),
        _code(
            """
            from app.data import documents_from_menu, load_policy_documents
            from app.text import normalize_text

            documents = documents_from_menu(snapshot.items) + load_policy_documents(DATA / "policies.json")
            document_frame = pd.DataFrame(
                [
                    {
                        "id": document.id,
                        "kind": document.kind,
                        "source": document.source,
                        "title": document.title,
                        "characters": len(document.text),
                    }
                    for document in documents
                ]
            )
            display(
                document_frame.groupby("kind").agg(
                    documents=("id", "count"), mean_characters=("characters", "mean")
                )
            )
            display(document_frame.head(8))

            examples = pd.DataFrame({"raw": ["Phở bò tái nạm", "quán có bún bò huế không"]})
            examples["normalized_for_lexical"] = examples["raw"].map(normalize_text)
            display(examples)
            """
        ),
        _markdown(
            """
            ## 4. Kiến trúc chatbot RAG và các phương án so sánh

                Menu PostgreSQL hiện tại + policy versioned
                    → document hóa và index in-memory
                    → retriever top-k
                    → fast path an toàn hoặc context cho LLM
                    → response kèm retrieved sources
                    → backend kiểm tra ID, giá, availability
                    → khách xác nhận hành động trên giao diện

            LLM chỉ diễn đạt khi có context phù hợp. Giá, policy, món hết và thao tác đặt món
            đi qua fast path hoặc backend. RAG không bắt buộc phải dùng vector database; corpus
            nhỏ, động và có kiểm soát vẫn có thể dùng index in-memory.
            """
        ),
        _code(
            """
            methods_frame = pd.DataFrame(
                [
                    {
                        "method": "tfidf",
                        "family": "lexical baseline",
                        "representation": "unigram + bigram TF-IDF",
                        "tuned_on_dev": "không có grid riêng",
                    },
                    {
                        "method": "bm25",
                        "family": "lexical baseline",
                        "representation": "BM25 + title boost",
                        "tuned_on_dev": "k1, b, title_boost",
                    },
                    {
                        "method": "embedding",
                        "family": "dense retrieval",
                        "representation": "FastEmbed multilingual MiniLM",
                        "tuned_on_dev": "embedding model",
                    },
                    {
                        "method": "hybrid_rrf",
                        "family": "hybrid",
                        "representation": "BM25 + dense, weighted RRF",
                        "tuned_on_dev": "rrf_k, lexical_weight",
                    },
                    {
                        "method": "hybrid_tfidf_embedding",
                        "family": "hybrid",
                        "representation": "TF-IDF + dense, weighted RRF",
                        "tuned_on_dev": "rrf_k, lexical_weight",
                    },
                ]
            )
            display(methods_frame)
            print("Không có reranker/cross-encoder trong scope hiện tại; không được ghi là đã so sánh.")
            """
        ),
        _markdown(
            """
            ## 5. Protocol đánh giá

            Development set chỉ dùng để tune threshold, BM25/RRF và chọn phương án. Frozen test
            chỉ báo cáo kết quả cho cấu hình đã khóa. Không dùng test để đổi winner production.

            Retrieval metrics: Hit@1, Hit@5, Recall@5, MRR@10, nDCG@10. Vận hành: answerability,
            P50/P95 latency. End-to-end chatbot: groundedness, citation coverage, hallucination,
            guardrail và task success.
            """
        ),
        _code(
            """
            split_count_by_group = case_frame.groupby("group_id")["split"].nunique()
            assert split_count_by_group.eq(1).all(), "Phát hiện leakage giữa development và test."

            protocol_frame = pd.DataFrame(
                [
                    {"phase": "development", "purpose": "tune và chọn phương án", "may_change_config": True},
                    {"phase": "frozen test", "purpose": "báo cáo cuối", "may_change_config": False},
                    {"phase": "production", "purpose": "deploy cấu hình phê duyệt", "may_change_config": False},
                ]
            )
            display(protocol_frame)
            print(f"PASS: kiểm tra {len(split_count_by_group)} group không leakage.")
            """
        ),
        _markdown(
            """
            ## 6. Tái chạy pipeline nghiên cứu

            Cell này không chạy mặc định vì nó ghi snapshot và artifact. Chỉ bật RUN_PIPELINE
            sau khi đã cài requirements-research, khóa source data và muốn tạo evidence bundle
            mới. Sau đó quay lại mục 1 để xác nhận checksum.
            """
        ),
        _code(
            """
            if RUN_PIPELINE:
                environment = {**os.environ, "PYTHONPATH": str(AI_ROOT)}
                for script in ("build_dataset.py", "run_experiments.py"):
                    command = [sys.executable, str(RESEARCH / script)]
                    print("Running:", " ".join(command))
                    subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)

                artifact_environment, provenance_frame, ARTIFACTS_FRESH = refresh_provenance()
                display(provenance_frame)
            else:
                print("Không chạy pipeline. Đặt RUN_PIPELINE=True để tạo artifact mới.")
            """
        ),
        _markdown(
            """
            ## 7. Tuning trên development set và quyết định trước test

            Quy tắc chọn: macro slice nDCG@10 cao nhất trên development; nếu các phương án cách
            nhau không quá 0,005 thì chọn P95 thấp hơn. Quyết định này phải được lưu trước khi
            nhìn frozen test. Nếu runner hiện tại còn ghi winner theo test, coi
            production_config đó là historical cho đến khi runner được sửa và pipeline được chạy lại.
            """
        ),
        _code(
            """
            required_artifacts = {
                "summary": ARTIFACTS / "summary.json",
                "statistics": ARTIFACTS / "statistical_tests.json",
                "per_query": ARTIFACTS / "per_query_results.csv",
            }
            missing_artifacts = [name for name, path in required_artifacts.items() if not path.exists()]

            if not ARTIFACTS_FRESH or missing_artifacts:
                summary = None
                statistics_payload = None
                per_query = None
                print("BLOCK: không đọc kết quả khi artifact chưa fresh.")
                if missing_artifacts:
                    print("Thiếu artifact:", ", ".join(missing_artifacts))
            else:
                summary = json.loads(required_artifacts["summary"].read_text(encoding="utf-8"))
                statistics_payload = json.loads(required_artifacts["statistics"].read_text(encoding="utf-8"))
                per_query = pd.read_csv(required_artifacts["per_query"])
                print("PASS: có artifact fresh để phân tích.")
            """
        ),
        _code(
            """
            SELECTION_TOLERANCE = 0.005

            if summary is not None:
                rows = []
                for method, payload in summary["methods"].items():
                    metrics = payload["dev"]
                    rows.append(
                        {
                            "method": method,
                            "macro_slice_nDCG@10": metrics["macro_slice_ndcg_at_10"],
                            "nDCG@10": metrics["ndcg_at_10"],
                            "P95 ms": metrics["latency_p95_ms"],
                            "threshold": payload["threshold"],
                            "config": payload["config"],
                        }
                    )
                development_frame = pd.DataFrame(rows).sort_values(
                    ["macro_slice_nDCG@10", "P95 ms"], ascending=[False, True]
                )
                best_quality = development_frame["macro_slice_nDCG@10"].max()
                finalists = development_frame[
                    best_quality - development_frame["macro_slice_nDCG@10"] <= SELECTION_TOLERANCE
                ]
                selected_method = finalists.sort_values("P95 ms").iloc[0]["method"]
                display(development_frame)
                print(f"Development-selected method: {selected_method}")
            else:
                selected_method = None
            """
        ),
        _markdown(
            """
            ## 8. Frozen test, kiểm định thống kê và error analysis

            Frozen test xác nhận phương án đã chọn và các baseline đã khai báo trước. Nó không
            được dùng để thay đổi winner production. Biểu đồ được tạo trực tiếp từ summary fresh,
            không phải ảnh PNG nhúng sẵn.
            """
        ),
        _code(
            """
            if summary is not None:
                test_rows = []
                slice_rows = []
                for method, payload in summary["methods"].items():
                    metrics = payload["test"]
                    test_rows.append(
                        {
                            "method": method,
                            "Hit@1": metrics["hit_at_1"],
                            "Hit@5": metrics["hit_at_5"],
                            "Recall@5": metrics["recall_at_5"],
                            "MRR@10": metrics["mrr_at_10"],
                            "nDCG@10": metrics["ndcg_at_10"],
                            "Macro slice nDCG@10": metrics["macro_slice_ndcg_at_10"],
                            "P95 ms": metrics["latency_p95_ms"],
                        }
                    )
                    for slice_name, slice_metrics in metrics["by_slice"].items():
                        if slice_metrics["ndcg_at_10"] >= 0:
                            slice_rows.append(
                                {
                                    "method": method,
                                    "slice": slice_name,
                                    "nDCG@10": slice_metrics["ndcg_at_10"],
                                }
                            )

                test_frame = pd.DataFrame(test_rows).sort_values("Macro slice nDCG@10", ascending=False)
                display(test_frame)

                figure, axes = plt.subplots(1, 2, figsize=(13, 4.5))
                ordered = test_frame.sort_values("Macro slice nDCG@10")
                axes[0].barh(ordered["method"], ordered["Macro slice nDCG@10"], color="#1f4e79")
                axes[0].set(xlim=(0, 1), xlabel="macro slice nDCG@10", title="Frozen-test retrieval quality")
                axes[1].barh(ordered["method"], ordered["P95 ms"], color="#c55a11")
                axes[1].set(xlabel="milliseconds", title="Frozen-test P95 latency")
                figure.tight_layout()
                plt.show()

                slice_frame = pd.DataFrame(slice_rows)
                axis = slice_frame.pivot(index="slice", columns="method", values="nDCG@10").plot(
                    kind="bar", figsize=(13, 5)
                )
                axis.set(ylim=(0, 1.05), ylabel="nDCG@10", title="Quality by query slice")
                plt.tight_layout()
                plt.show()
            """
        ),
        _code(
            """
            if summary is not None:
                stats_frame = pd.DataFrame(
                    [
                        {
                            "compared_with_selected": method,
                            "paired_nDCG_delta": value["paired_ndcg_delta_winner_minus_method"],
                            "bootstrap_95_ci": value["paired_bootstrap_95_ci"],
                            "McNemar_p": value["mcnemar"]["exact_two_sided_p"],
                        }
                        for method, value in statistics_payload.items()
                    ]
                )
                display(stats_frame)

                if selected_method and per_query is not None:
                    selected_rows = per_query[per_query["method"] == selected_method].copy()
                    selected_rows["hit_at_5"] = pd.to_numeric(selected_rows["hit_at_5"], errors="coerce")
                    failures = selected_rows[
                        selected_rows["expected_ids"].fillna("").ne("")
                        & (selected_rows["hit_at_5"].fillna(0) < 1)
                    ].sort_values(["slice", "question"])
                    display(failures[["slice", "question", "expected_ids", "retrieved_ids", "top_score"]].head(20))
            """
        ),
        _markdown(
            """
            ## 9. Demo retrieval → context → chatbot

            Demo mặc định chỉ dựng evidence context, không gửi dữ liệu ra ngoài. Khi AI service
            cục bộ đã chạy, bật RUN_LIVE_SERVICE_DEMO để gọi API thật và kiểm tra response,
            retrieved sources, guardrail flags cùng latency.
            """
        ),
        _code(
            """
            from app.retrieval import TfidfRetriever

            DEMO_QUERY = "Gợi ý món nước nóng có thịt bò"
            demo_results = TfidfRetriever(documents).search(DEMO_QUERY, top_k=3)
            demo_context = pd.DataFrame(
                [
                    {
                        "rank": result.rank,
                        "document_id": result.document.id,
                        "title": result.document.title,
                        "score": result.score,
                        "context": result.document.answer or result.document.text,
                    }
                    for result in demo_results
                ]
            )
            display(demo_context)
            print("Chỉ evidence trên được phép đi vào prompt; LLM không được tạo menu, giá hoặc policy mới.")
            """
        ),
        _code(
            """
            if RUN_LIVE_SERVICE_DEMO:
                import httpx

                payload = {
                    "message": DEMO_QUERY,
                    "history": [],
                    "table_code": "DEMO",
                    "menu_items": [item.to_mapping() for item in snapshot.items],
                }
                response = httpx.post(f"{AI_SERVICE_URL}/v1/chat", json=payload, timeout=15)
                response.raise_for_status()
                live_response = response.json()
                display(pd.DataFrame(live_response.get("retrieved_sources", [])))
                display(
                    pd.DataFrame(
                        [
                            {
                                "content": live_response.get("content"),
                                "provider_available": live_response.get("provider_available"),
                                "retrieval_method": live_response.get("retrieval_method"),
                                "guardrail_flags": live_response.get("guardrail_flags"),
                                "latency_ms": live_response.get("latency_ms"),
                            }
                        ]
                    )
                )
            else:
                print("Không gọi service. Đặt RUN_LIVE_SERVICE_DEMO=True sau khi service cục bộ sẵn sàng.")
            """
        ),
        _markdown(
            """
            ## 10. Đánh giá generation, safety và checklist phát hành

            Retrieval tốt không tự động chứng minh chatbot tốt. Khi có user log ẩn danh hoặc tập
            đánh giá gán nhãn độc lập, dùng rubric dưới đây cho end-to-end evaluation. Không
            báo cáo production-ready khi provenance gate còn BLOCK.
            """
        ),
        _code(
            """
            generation_rubric = pd.DataFrame(
                [
                    {
                        "dimension": "groundedness",
                        "metric": "claim-level support rate",
                        "target": "100% cho giá, availability và policy",
                    },
                    {
                        "dimension": "citation coverage",
                        "metric": "source coverage",
                        "target": "100% response có retrieval",
                    },
                    {
                        "dimension": "safety",
                        "metric": "guardrail violation rate",
                        "target": "0%",
                    },
                    {
                        "dimension": "task success",
                        "metric": "human success rate",
                        "target": "đặt trước trong study protocol",
                    },
                ]
            )
            release_checklist = pd.DataFrame(
                [
                    {"check": "Artifact provenance fresh", "status": "PASS" if ARTIFACTS_FRESH else "BLOCK"},
                    {"check": "No group leakage", "status": "PASS"},
                    {"check": "Development-based selection recorded", "status": "TODO"},
                    {"check": "Frozen test after selection", "status": "TODO"},
                    {"check": "Groundedness and safety evaluation", "status": "TODO"},
                    {"check": "UI renders retrieved sources", "status": "TODO"},
                ]
            )
            display(generation_rubric)
            display(release_checklist)
            """
        ),
    ]

    for index, cell in enumerate(cells):
        cell["id"] = f"rag-{index:02d}"

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


def _markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(source)}


def _code(source: str, tags: list[str] | None = None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": tags or []},
        "outputs": [],
        "source": _lines(source),
    }


def _lines(source: str) -> list[str]:
    text = dedent(source).strip() + "\n"
    return text.splitlines(keepends=True)


if __name__ == "__main__":
    main()
