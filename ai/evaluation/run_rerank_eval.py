# -*- coding: utf-8 -*-
"""Xếp hạng lại bằng cross-encoder có đáng bật không — đo ở ĐÚNG k hệ thống dùng.

Vì sao phép đo này phải tồn tại lần thứ hai
-------------------------------------------
Lần đo trước chấm ở **Hit@1**: lấy 10 ứng viên rồi chọn đúng MỘT đoạn. Kết luận khi đó là không đủ
ý nghĩa thống kê, và bị bỏ.

Nhưng `answer.SO_DOAN_TRI_THUC` đã lên 2, nên phép đo ấy chấm một hệ thống **không còn tồn tại** —
đúng lớp sai vừa phải sửa trong `run_retrieval_comparison.py`, nơi bảng báo Hit@1 trong khi hệ thống
chạy ở k=2 và tự bôi đen nhánh RAG 17,85 điểm.

Và k không phải chi tiết nhỏ với reranker. Ở k=1 nó phải đưa đoạn đúng lên **hạng nhất**; ở k=2 chỉ
cần vào **hai hạng đầu**. Bài toán dễ hơn hẳn, nên kết luận cũ có thể lật. Không đo lại thì không
biết — và "chúng tôi từng đo ở k khác" không phải một câu trả lời.

Ba mặt, không chỉ mặt lợi
-------------------------
    trúng@k   có chạm tài liệu đích không
    CẤM@k     có vơ phải đoạn thuộc chủ đề câu hỏi KHÔNG được chạm không   <- mặt an toàn
    ms/câu    chi phí, đo trong CÙNG lượt chạy với hai cột trên

Cột `CẤM@k` là cột dễ quên nhất: một bộ xếp hạng "giỏi hơn" mà kéo theo đoạn lạc chủ đề thì nó
không giỏi hơn, nó chỉ tự tin hơn.

Độ trễ đo trong cùng một lượt với phần đúng/sai — cố ý. Đo riêng ở lượt khác thì hai cột không cùng
điều kiện máy, và chênh lệch điều kiện đủ để lật một kết luận về chi phí.

Sinh lại
--------
    python ai/evaluation/run_rerank_eval.py            # đầy đủ, GHI kết quả
    python ai/evaluation/run_rerank_eval.py --gioi-han 20   # thử nhanh, KHÔNG ghi

`--gioi-han` không ghi: một lượt 20 ca ghi đè kết quả 152 ca sẽ cho một con số đúng về chính nó và
sai về thứ đang được nói.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))
sys.path.insert(0, str(HERE))

import chunk_selectors as CS          # noqa: E402
import results                        # noqa: E402
import rag.embedding as EMB           # noqa: E402
from rag.chunker import doan_toan_kho  # noqa: E402
from rag.embedding import EmbeddingIndex  # noqa: E402
from thong_ke import khoang_wilson, mcnemar  # noqa: E402

KHO = REPO_ROOT / "ai" / "knowledge"
MO_HINH_XEP_LAI = "BAAI/bge-reranker-v2-m3"

# Số ứng viên đưa vào bộ xếp lại. Giữ 10 để so được với lần đo trước.
#
# Đây cũng là TRẦN của phép đo: đoạn đúng không nằm trong 10 ứng viên thì bộ xếp lại bó tay. Trần đó
# không phải chỗ thắt — Hit@5 của nền đã là 0,917 trên nhóm `written` — nhưng phải nói ra, vì một
# kết quả âm tính mà giấu trần đo thì không kiểm chứng được.
K_UNG_VIEN = 10


def so_doan_van_hanh() -> int:
    """Đọc số đoạn từ chính `answer.py` thay vì viết lại con số."""
    try:
        import answer

        return answer.SO_DOAN_TRI_THUC
    except Exception:  # pragma: no cover - chỉ xảy ra khi `ai/app` không nạp được
        return 2


def giu_k_theo_tai_lieu(thu_tu: list[str], doc_cua: dict[str, str], k: int) -> list[str]:
    """Khử trùng theo TÀI LIỆU rồi giữ k chunk_id — đúng như `answer.chon_doan_tri_thuc`.

    Không khử trùng thì hai đoạn của cùng một tài liệu chiếm cả hai suất, và phép đo sẽ khoan dung
    hơn hệ thống thật.
    """
    da_co: set[str] = set()
    giu: list[str] = []
    for cid in thu_tu:
        doc = doc_cua[cid]
        if doc in da_co:
            continue
        da_co.add(doc)
        giu.append(cid)
        if len(giu) >= k:
            break
    return giu


def nap_ca() -> tuple[list[str], list[set], list[set]]:
    """Câu hỏi kèm tập chunk_id đích và tập chunk_id CẤM, lấy từ hai tập đã chia."""
    cases = json.loads((HERE / "retrieval_cases.json").read_text(encoding="utf-8"))["cases"]
    split = json.loads((HERE / "retrieval_split.json").read_text(encoding="utf-8"))
    ho = set(split["gate_families"]) | set(split["dev_families"])

    cau, dich, cam = [], [], []
    for c in cases:
        if c["family"] not in ho or c.get("expect_nothing"):
            continue
        d = CS.select_many(c["expected"]) if c.get("expected") else set()
        if not d:
            continue
        cau.append(c["query"])
        dich.append(d)
        cam.append(CS.select_many(c["forbidden"]) if c.get("forbidden") else set())
    return cau, dich, cam


def cham(thu_list, doc_cua, dich, cam, k):
    trung, dinh_cam = [], []
    for i, thu in enumerate(thu_list):
        ids = set(giu_k_theo_tai_lieu(thu, doc_cua, k))
        trung.append(bool(ids & dich[i]))
        dinh_cam.append(bool(ids & cam[i]))
    return trung, dinh_cam


def p95(v: list[float]) -> float:
    return sorted(v)[int(0.95 * len(v)) - 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gioi-han", type=int, default=0,
                    help="chỉ chạy N ca đầu để thử nhanh; lượt này KHÔNG ghi kết quả")
    args = ap.parse_args()

    from sentence_transformers import CrossEncoder

    k = so_doan_van_hanh()
    doan = doan_toan_kho(KHO)
    van_ban = {c.chunk_id: c.text for c in doan}
    doc_cua = {c.chunk_id: c.doc_id for c in doan}
    cau, dich, cam = nap_ca()
    if args.gioi_han:
        cau, dich, cam = cau[:args.gioi_han], dich[:args.gioi_han], cam[:args.gioi_han]
    n = len(cau)
    print(f"  {n} ca · {len(doan)} đoạn · {K_UNG_VIEN} ứng viên -> giữ {k}\n", flush=True)

    # Dùng CHÍNH `EmbeddingIndex` của hệ thống, không dựng lại phép so vector ở đây.
    #
    # Hai lý do. Một: nó đọc đệm vector tính sẵn (`AI_EMBEDDING_CACHE`), nên phép đo không tốn lại
    # nhiều phút mã hóa kho mỗi lần chạy. Hai — quan trọng hơn — một bản dựng lại sẽ đo bản dựng
    # lại chứ không đo hệ thống, và mọi khác biệt nhỏ (tiền tố `query:`/`passage:`, cách chuẩn hóa,
    # cách phá hòa điểm) đều là chỗ kết luận có thể lệch mà không ai thấy.
    chi_muc = EmbeddingIndex.build(doan)
    print(f"  chỉ mục: {len(chi_muc.chunk_ids)} vector, "
          f"{'từ đệm' if chi_muc.tu_dem else 'vừa mã hóa lại'}", flush=True)

    tre_nen, ung_vien = [], []
    for q in cau:
        t = time.perf_counter()
        thu = [h.chunk_id for h in chi_muc.search(q, k=K_UNG_VIEN)]
        tre_nen.append((time.perf_counter() - t) * 1000)
        ung_vien.append(thu)

    print(f"  nạp {MO_HINH_XEP_LAI} ...", flush=True)
    ce = CrossEncoder(MO_HINH_XEP_LAI, max_length=512)

    tre_xep, thu_xep = [], []
    for i, q in enumerate(cau):
        t = time.perf_counter()
        cap = [(q, van_ban[cid]) for cid in ung_vien[i]]
        diem = ce.predict(cap, batch_size=len(cap), show_progress_bar=False)
        thu_xep.append([cid for _, cid in sorted(
            zip(diem, ung_vien[i]), key=lambda p: -float(p[0]))])
        tre_xep.append((time.perf_counter() - t) * 1000)
        if (i + 1) % 25 == 0:
            print(f"    {i+1}/{n}  ({statistics.median(tre_xep):.0f} ms/câu)", flush=True)

    trung_nen, cam_nen = cham(ung_vien, doc_cua, dich, cam, k)
    trung_xep, cam_xep = cham(thu_xep, doc_cua, dich, cam, k)

    print(f"\n  {'phương pháp':24} {f'trúng@{k}':>9} {'KTC 95%':>16} {f'CẤM@{k}':>8} "
          f"{'p50 ms':>9} {'p95 ms':>9}")
    print("  " + "-" * 82)
    for ten, tr, cm, lat in (
        (f"{EMB.MODEL_NAME} (nền)", trung_nen, cam_nen, tre_nen),
        (f"+ xếp lại top-{K_UNG_VIEN}", trung_xep, cam_xep, tre_xep),
    ):
        w = khoang_wilson(sum(tr), n)
        print(f"  {ten:24} {w.ty_le*100:8.2f}% {w.duoi*100:7.2f}–{w.tren*100:6.2f}% "
              f"{sum(cm)/n*100:7.2f}% {statistics.median(lat):9.0f} {p95(lat):9.0f}")

    r_dung = mcnemar(trung_xep, trung_nen)
    r_cam = mcnemar(cam_xep, cam_nen)
    cham_hon = statistics.median(tre_xep) / max(statistics.median(tre_nen), 1e-9)
    print(f"\n  {r_dung.ket_luan('xếp lại', 'nền')}")
    print(f"    tốt lên {r_dung.chi_a_dung} ca · xấu đi {r_dung.chi_b_dung} ca · p = {r_dung.p:.4f}")
    print(f"  an toàn (CẤM@{k}, thấp hơn là tốt): xếp lại {sum(cam_xep)} ca, nền {sum(cam_nen)} ca, "
          f"p = {r_cam.p:.4f}")
    print(f"  chi phí: chậm hơn nền {cham_hon:.0f}× "
          f"({statistics.median(tre_nen):.0f} ms -> {statistics.median(tre_xep):.0f} ms)")

    if args.gioi_han:
        print("\n  --gioi-han: KHÔNG ghi kết quả (lượt rút gọn không thay được lượt đầy đủ).")
        return 0

    duong = results.ghi(
        "xep_lai",
        {
            "so_ca": n,
            "so_doan_giu": k,
            "so_ung_vien": K_UNG_VIEN,
            "nen": {
                "trung": sum(trung_nen) / n,
                "cam": sum(cam_nen) / n,
                "p50_ms": statistics.median(tre_nen),
                "p95_ms": p95(tre_nen),
            },
            "xep_lai": {
                "trung": sum(trung_xep) / n,
                "cam": sum(cam_xep) / n,
                "p50_ms": statistics.median(tre_xep),
                "p95_ms": p95(tre_xep),
            },
            "mcnemar_dung": {"tot_len": r_dung.chi_a_dung, "xau_di": r_dung.chi_b_dung,
                             "p": r_dung.p},
            "mcnemar_cam": {"p": r_cam.p},
            "cham_hon_lan": cham_hon,
        },
        {
            "mo_hinh_nhung": EMB.MODEL_NAME,
            "mo_hinh_xep_lai": MO_HINH_XEP_LAI,
            "so_doan_tri_thuc": k,
            "so_doan_trong_kho": len(doan),
            "thiet_bi": "CPU",
            "ghi_chu_do_tre": (
                "Độ trễ đo trong CÙNG lượt với phần đúng/sai. Chi phí mỗi câu thay đổi rất rộng "
                "theo độ dài các đoạn được lấy — cross-encoder tính theo số token, mà đoạn trong "
                "kho dài ngắn khác nhau nhiều. Nên đọc p50 cùng p95, đừng đọc p50 một mình."
            ),
        },
    )
    print(f"\n  Đã ghi {duong.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
