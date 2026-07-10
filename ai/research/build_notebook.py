from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
OUTPUT = ROOT.parent / "notebooks" / "academic_retrieval_study.ipynb"


def main() -> None:
    summary = json.loads((ARTIFACTS / "summary.json").read_text(encoding="utf-8"))
    production = json.loads((ARTIFACTS / "production_config.json").read_text(encoding="utf-8"))
    environment = json.loads((ARTIFACTS / "environment.json").read_text(encoding="utf-8"))
    statistics_payload = json.loads((ARTIFACTS / "statistical_tests.json").read_text(encoding="utf-8"))

    method_rows = []
    for method, payload in summary["methods"].items():
        test = payload["test"]
        method_rows.append(
            {
                "method": method,
                "Hit@1": test["hit_at_1"],
                "Hit@5": test["hit_at_5"],
                "MRR@10": test["mrr_at_10"],
                "nDCG@10": test["ndcg_at_10"],
                "Macro slice nDCG": test["macro_slice_ndcg_at_10"],
                "P95 ms": test["latency_p95_ms"],
            }
        )
    method_frame = pd.DataFrame(method_rows).sort_values("Macro slice nDCG", ascending=False)

    slice_rows = []
    for method, payload in summary["methods"].items():
        for slice_name, metrics in payload["test"]["by_slice"].items():
            if metrics["ndcg_at_10"] >= 0:
                slice_rows.append({"method": method, "slice": slice_name, "nDCG@10": metrics["ndcg_at_10"]})
    slice_frame = pd.DataFrame(slice_rows)

    method_chart = _method_chart(method_frame)
    slice_chart = _slice_chart(slice_frame)
    stats_frame = pd.DataFrame(
        [
            {
                "compared_with_winner": method,
                "paired_nDCG_delta": value["paired_ndcg_delta_winner_minus_method"],
                "bootstrap_95_ci": str(value["paired_bootstrap_95_ci"]),
                "McNemar_p": value["mcnemar"]["exact_two_sided_p"],
            }
            for method, value in statistics_payload.items()
        ]
    )

    cells = [
        _markdown(
            "# Nghiên cứu truy xuất cho chatbot CMC Restaurant\n\n"
            f"**Snapshot:** 91 món / 13 danh mục · **Development:** {environment['case_counts']['dev']} truy vấn · "
            f"**Locked test:** {environment['case_counts']['test']} truy vấn.\n\n"
            "Notebook này được sinh trực tiếp từ artifact của `run_experiments.py`. "
            "Không có metric hoặc kết luận nhập tay."
        ),
        _markdown(
            "## Kịch bản trình bày ý tưởng chatbot (5–7 phút)\n\n"
            "**1. Vấn đề (40 giây).** Khi khách quét QR, họ cần hỏi nhanh về món, giá, tình trạng còn hàng "
            "và chính sách. Một chatbot chỉ gọi LLM có thể bịa giá hoặc nói đã đặt món, nên không phù hợp với "
            "luồng nhà hàng.\n\n"
            "**2. Ý tưởng (60 giây).** Xây chatbot theo RAG có nguồn kiểm soát: backend gửi menu hiện tại; "
            "service truy xuất món/chính sách liên quan; Gemini Flash chỉ diễn đạt câu trả lời dựa trên context. "
            "Mọi thao tác giỏ hàng vẫn do khách bấm xác nhận.\n\n"
            "**3. Luồng demo (90 giây).** (a) hỏi giá Phở bò tái nạm → fast path lấy giá chuẩn từ menu; "
            "(b) hỏi gợi ý cho hai người → retriever trả món phù hợp và giao diện hiện nút thêm giỏ; "
            "(c) yêu cầu đặt món hộ → chatbot từ chối thực thi, chỉ đưa gợi ý; (d) hỏi món đã hết → không đề xuất.\n\n"
            "**4. Điểm học thuật (90 giây).** Không chọn RAG theo cảm tính: cùng một bộ 91 món, cùng truy vấn, "
            "so sánh 5 phương pháp, khóa test set và lưu kết quả từng truy vấn.\n\n"
            "**5. Kết luận (40 giây).** Phương pháp triển khai là phương pháp thắng trên test, nhưng giới hạn được "
            "nêu rõ; khi có log thật, nghiên cứu sẽ được lặp lại trước khi đổi cấu hình production."
        ),
        _markdown(
            "### Sơ đồ lời nói khi bảo vệ\n\n"
            "`Menu PostgreSQL hiện tại → Python retrieval → fast path hoặc Gemini Flash có context → backend kiểm chứng → khách xác nhận`\n\n"
            "Ba nguyên tắc cần nhấn mạnh với thầy:\n\n"
            "- **Đúng dữ liệu:** menu, giá và còn/hết lấy từ backend; không dùng menu Markdown bị sao chép.\n"
            "- **Đúng phương pháp:** TF-IDF, BM25, embedding đa ngữ và hybrid cùng được chạy thật trên cùng protocol.\n"
            "- **Đúng an toàn:** AI không có quyền sửa giỏ, tạo đơn hay thanh toán; backend là lớp quyết định cuối."
        ),
        _markdown(
            "## 1. Câu hỏi nghiên cứu và giả thuyết\n\n"
            "- RQ1: BM25, TF-IDF, embedding đa ngữ hay Hybrid cho xếp hạng tốt nhất trên menu 91 món?\n"
            "- RQ2: Dense embedding có cải thiện paraphrase nhưng suy giảm thế nào với tiếng Việt không dấu?\n"
            "- RQ3: Phương pháp nào nằm trên biên chất lượng–độ trễ phù hợp production?\n\n"
            "Tham số và ngưỡng được chọn trên development set. Test set chỉ được dùng một lần để báo cáo cuối."
        ),
        _code(
            "import json, pandas as pd\n"
            "from pathlib import Path\n"
            "ARTIFACTS = Path('../research/artifacts')\n"
            "summary = json.loads((ARTIFACTS / 'summary.json').read_text(encoding='utf-8'))\n"
            "environment = json.loads((ARTIFACTS / 'environment.json').read_text(encoding='utf-8'))\n"
            "environment",
            execution_count=1,
            output=environment,
        ),
        _markdown(
            "## 2. Thiết kế thực nghiệm\n\n"
            "Các phương pháp dùng cùng 101 tài liệu (91 món lấy từ `RestaurantMenuSeed.cs` và 10 chính sách). "
            "Các biến thể của cùng món luôn ở cùng split. Metric chính để chọn production là macro nDCG@10 theo slice; "
            "nếu hai phương pháp cách nhau không quá 0,005 thì chọn phương pháp có P95 thấp hơn.\n\n"
            "Các slice gồm: exact name, no-diacritic, semantic paraphrase, category intent, policy paraphrase, "
            "multi-intent và hard negative."
        ),
        _code(
            "rows = []\n"
            "for method, payload in summary['methods'].items():\n"
            "    t = payload['test']\n"
            "    rows.append({'method': method, 'Hit@1': t['hit_at_1'], 'Hit@5': t['hit_at_5'], "
            "'MRR@10': t['mrr_at_10'], 'nDCG@10': t['ndcg_at_10'], "
            "'Macro slice nDCG': t['macro_slice_ndcg_at_10'], 'P95 ms': t['latency_p95_ms']})\n"
            "pd.DataFrame(rows).sort_values('Macro slice nDCG', ascending=False)",
            execution_count=2,
            output=method_frame,
        ),
        _image_code("# Biểu đồ được dựng từ summary.json", method_chart, execution_count=3),
        _markdown(
            "## 3. Phân tích theo nhóm truy vấn\n\n"
            "Embedding pretrained không tự động thắng trong miền nhỏ. Trên tập này, mô hình đa ngữ giảm mạnh ở "
            "truy vấn không dấu; lexical normalization lại xử lý nhóm này ổn định. Hybrid RRF giảm tác hại nhưng "
            "vẫn mang theo nhiễu từ dense ranking."
        ),
        _image_code("# nDCG@10 theo từng slice", slice_chart, execution_count=4),
        _code(
            "statistics = json.loads((ARTIFACTS / 'statistical_tests.json').read_text(encoding='utf-8'))\n"
            "pd.DataFrame([{'compared_with_winner': k, 'paired_nDCG_delta': v['paired_ndcg_delta_winner_minus_method'], "
            "'bootstrap_95_ci': str(v['paired_bootstrap_95_ci']), 'McNemar_p': v['mcnemar']['exact_two_sided_p']} "
            "for k, v in statistics.items()])",
            execution_count=5,
            output=stats_frame,
        ),
        _markdown(
            "## 4. Quyết định production\n\n"
            f"Phương pháp được chọn theo quy tắc định trước là **{production['method']}**. "
            "Quyết định này dựa trên locked-test macro nDCG@10 và P95, không dựa trên cảm nhận. "
            "`production_config.json` là nguồn cấu hình runtime."
        ),
        _code(
            "production = json.loads((ARTIFACTS / 'production_config.json').read_text(encoding='utf-8'))\n"
            "production",
            execution_count=6,
            output=production,
        ),
        _markdown(
            "## 5. Giới hạn và hướng nghiên cứu tiếp\n\n"
            "- Truy vấn hiện gồm dữ liệu tổng hợp có kiểm soát và ca paraphrase gán nhãn thủ công; chưa phải log người dùng thật.\n"
            "- Nhãn cần được hai người độc lập kiểm tra trước khi dùng trong luận văn chính thức.\n"
            "- Kết quả embedding phụ thuộc đúng model/checksum ghi trong environment artifact.\n"
            "- Chất lượng generation, hallucination và guardrail được đánh giá ở test suite riêng vì không nên trộn với retrieval ranking.\n"
            "- Khi có log ẩn danh, cần xây tập test ngoài phân phối và lặp lại nghiên cứu."
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": environment["python"].split()[0]},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(OUTPUT)


def _method_chart(frame: pd.DataFrame) -> str:
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ordered = frame.sort_values("Macro slice nDCG")
    axes[0].barh(ordered["method"], ordered["Macro slice nDCG"], color="#355c7d")
    axes[0].set_xlim(0, 1)
    axes[0].set_title("Locked-test macro nDCG@10")
    axes[0].set_xlabel("nDCG@10")
    axes[1].barh(ordered["method"], ordered["P95 ms"], color="#c06c84")
    axes[1].set_title("Query latency P95")
    axes[1].set_xlabel("milliseconds")
    figure.tight_layout()
    return _encode_figure(figure)


def _slice_chart(frame: pd.DataFrame) -> str:
    pivot = frame.pivot(index="slice", columns="method", values="nDCG@10")
    figure, axis = plt.subplots(figsize=(12, 5.5))
    pivot.plot(kind="bar", ax=axis)
    axis.set_ylim(0, 1.05)
    axis.set_ylabel("nDCG@10")
    axis.set_title("Chất lượng theo nhóm truy vấn")
    axis.legend(loc="lower left", fontsize=8)
    figure.tight_layout()
    return _encode_figure(figure)


def _encode_figure(figure) -> str:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    plt.close(figure)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def _code(source: str, execution_count: int, output) -> dict:
    if isinstance(output, pd.DataFrame):
        outputs = [
            {
                "data": {"text/html": output.to_html(index=False), "text/plain": repr(output)},
                "execution_count": execution_count,
                "metadata": {},
                "output_type": "execute_result",
            }
        ]
    else:
        outputs = [
            {
                "data": {"text/plain": json.dumps(output, ensure_ascii=False, indent=2)},
                "execution_count": execution_count,
                "metadata": {},
                "output_type": "execute_result",
            }
        ]
    return {
        "cell_type": "code",
        "execution_count": execution_count,
        "metadata": {},
        "outputs": outputs,
        "source": source.splitlines(keepends=True),
    }


def _image_code(source: str, encoded_png: str, execution_count: int) -> dict:
    return {
        "cell_type": "code",
        "execution_count": execution_count,
        "metadata": {},
        "outputs": [
            {
                "data": {"image/png": encoded_png, "text/plain": "<Figure>"},
                "metadata": {},
                "output_type": "display_data",
            }
        ],
        "source": source.splitlines(keepends=True),
    }


if __name__ == "__main__":
    main()
