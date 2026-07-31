# -*- coding: utf-8 -*-
"""So BM25 / embedding / hybrid trên bài toán CHỌN MỤC TRONG TÀI LIỆU.

    python ai/evaluation/run_chunk_selection_comparison.py
    python ai/evaluation/run_chunk_selection_comparison.py --sealed
    python ai/evaluation/run_chunk_selection_comparison.py --chi-tiet

Cần `pip install -r ai/requirements.txt` cho phần embedding. Không có thì bộ này in rõ đã bỏ qua
phương pháp nào — nó KHÔNG im lặng so hai phương pháp rồi gọi đó là so ba.

Chỉ số CHÍNH là Top-1, không phải Hit@5
---------------------------------------
`answer.py::_knowledge_chunk` gọi `search(question, k=1)` và dùng đúng đoạn đầu. Nên Hit@5 ở bài
toán này là chỉ số của một hệ thống KHÔNG TỒN TẠI: không có nhánh nào đọc đoạn thứ hai.

Số ứng viên mỗi ca chỉ 3–7, nên sàn ngẫu nhiên khoảng 1/4,9 ≈ 20%. Một phương pháp đạt 60% nghe cao
nhưng chỉ hơn sàn 3 lần — con số phải đọc cùng sàn đó, và bộ này in nó ra.

MRR vẫn được in vì nó cho biết khi sai thì sai XA hay GẦN. Sai mà đoạn đúng nằm hạng 2 khác hẳn sai
mà nó nằm hạng cuối, và nếu chênh lệch giữa các phương pháp nằm hết ở đó thì Top-1 che mất.

Tách dạng A và dạng B, và đó là điểm chính của phép so
------------------------------------------------------
Dạng A dùng từ có trong mục; dạng B diễn đạt khác. Một phương pháp thắng ở A mà thua ở B là một
phương pháp khớp từ khóa; thắng cả hai mới là hiểu nghĩa. Gộp hai dạng thành một số làm mất đúng
thông tin cần để chọn.

Nhóm `derived` báo cáo RIÊNG: nó là MỘT quyết định lặp trên 6 tài liệu, nên gộp vào số chính sẽ để
một bài toán dễ kéo con số lên.
"""
from __future__ import annotations

import argparse
import datetime
import json
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

from rag import embedding as EMB  # noqa: E402
from rag.bm25 import Bm25Index  # noqa: E402
from rag.chunker import retrievable_chunks  # noqa: E402
from rag.hybrid import HybridRetriever  # noqa: E402

KNOWLEDGE = REPO_ROOT / "ai" / "knowledge"
CASES_PATH = HERE / "chunk_selection_cases.json"
SPLIT_PATH = HERE / "chunk_selection_split.json"

# Số lần chạy để đo độ trễ. Giao thức `release` chạy 7 lần và lấy trung vị — cùng giao thức với
# `run_retrieval_comparison.py`, vì trộn hai giao thức đo rồi so 29ms với 81ms như cùng loại là lỗi
# đã mắc một lần ở bản trước.
LATENCY_RUNS = 7


@dataclass
class Ketqua:
    ten: str
    top1: list[float] = field(default_factory=list)
    mrr: list[float] = field(default_factory=list)
    so_ung_vien: list[int] = field(default_factory=list)
    latency_ms: list[float] = field(default_factory=list)
    sai: list[tuple[str, str, str, int]] = field(default_factory=list)

    def them(self, case: dict, xep_hang: list[str], ms: float) -> None:
        dung = case["expected_chunk_id"]
        self.so_ung_vien.append(len(case["candidates"]))
        self.latency_ms.append(ms)
        ok = bool(xep_hang) and xep_hang[0] == dung
        self.top1.append(1.0 if ok else 0.0)
        try:
            hang = xep_hang.index(dung) + 1
        except ValueError:
            hang = 0
        self.mrr.append(1.0 / hang if hang else 0.0)
        if not ok:
            self.sai.append((case["id"], case["query"], dung, hang))

    @property
    def n(self) -> int:
        return len(self.top1)

    def dong(self) -> str:
        if not self.n:
            return f"  {self.ten:<24} (không ca nào)"
        san = 1.0 / statistics.fmean(self.so_ung_vien)
        return (f"  {self.ten:<24} Top-1 {statistics.fmean(self.top1):.3f}   "
                f"MRR {statistics.fmean(self.mrr):.3f}   "
                f"sàn {san:.3f}   n={self.n}   "
                f"p50 {statistics.median(self.latency_ms):.1f}ms")


def build_retrievers() -> dict[str, object]:
    """Ba phương pháp. Embedding thiếu thì NÓI RA, không im lặng bỏ."""
    ra: dict[str, object] = {"bm25": "bm25"}
    if EMB.available():
        ra["embedding"] = "embedding"
        ra["hybrid"] = "hybrid"
    else:
        print(f"BỎ QUA embedding và hybrid: {EMB.why_unavailable()}")
        print("  Cài `pip install -r ai/requirements.txt` để so đủ ba phương pháp.\n")
    return ra


_CHI_MUC: dict[tuple[str, str], object] = {}


def chi_muc(kind: str, doc_id: str, cands: list):
    """Chỉ mục của MỘT tài liệu, dựng một lần rồi dùng lại.

    Dựng lại cho từng ca thì embedding phải mã hóa lại 3–7 đoạn mỗi lần, và phép đo độ trễ sẽ đo
    việc mã hóa chứ không đo việc tìm. Một triển khai embedding thật tính vector đoạn lúc khởi động.

    Ba cách dựng chỉ mục, và p50 dưới đây chỉ đo MỘT trong ba — ghi ra chứ không lặng lẽ so
    -----------------------------------------------------------------------------------
        phép đo này            dựng chỉ mục cho MỖI tài liệu, một lần rồi dùng lại (bảng `_CHI_MUC`)
        runtime · embedding    KHÔNG dựng gì. `answer.py::_chon_muc` dùng lại vector của chỉ mục
                               TOÀN KHO đã nạp sẵn lúc khởi động, chỉ mã hóa CÂU HỎI một lần. Nên
                               chi phí thật của embedding lúc chạy **thấp hơn** p50 dưới đây.
        runtime · BM25 (lùi)   dựng lại mỗi lượt. Rẻ với 3–7 đoạn, nhưng nó có nghĩa là p50 của BM25
                               dưới đây **thấp hơn** chi phí thật.

    Hai chiều lệch ngược nhau, nên p50 ở đây không dùng để so chi phí runtime giữa hai phương pháp.
    Nó chỉ dùng để so ĐỘ CHÍNH XÁC dưới cùng một điều kiện.
    """
    key = (kind, doc_id)
    if key not in _CHI_MUC:
        if kind == "bm25":
            _CHI_MUC[key] = Bm25Index.build(cands)
        elif kind == "embedding":
            _CHI_MUC[key] = EMB.EmbeddingIndex.build(cands)
        else:
            _CHI_MUC[key] = HybridRetriever(retrievers=[
                Bm25Index.build(cands), EMB.EmbeddingIndex.build(cands),
            ], depth=len(cands))
    return _CHI_MUC[key]


def xep_hang(kind: str, doc_id: str, cands: list, query: str) -> list[str]:
    """Xếp hạng các ứng viên của MỘT tài liệu. Trả về dãy chunk_id theo thứ tự."""
    hits = chi_muc(kind, doc_id, cands).search(query, k=len(cands))
    return [h.chunk_id for h in hits]


def nap(sealed: bool) -> tuple[list[dict], set[str], dict[str, list]]:
    """Ca của một nhóm split, kèm bảng đoạn theo tài liệu. Tách ra để notebook dùng lại được."""
    data = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8-sig"))
    hos = set(split["test_families"] if sealed else split["dev_families"])
    cases = [c for c in data["cases"] if c["family"] in hos]

    theo_doc: dict[str, list] = defaultdict(list)
    for c in retrievable_chunks(KNOWLEDGE):
        theo_doc[c.doc_id].append(c)
    return cases, hos, theo_doc


def do_lat(cases: list[dict], retrievers: dict, theo_doc: dict[str, list],
           *, runs: int = LATENCY_RUNS) -> dict[tuple[str, str], dict[str, Ketqua]]:
    """Đo bốn lát (nhóm × dạng câu) cho mọi bộ xếp hạng.

    Tách khỏi `main()` vì notebook phải TÍNH LẠI những con số này, không được chép chúng. Con số
    chép tay trong notebook đã trôi ba lần trong dự án này — xem `ai/evaluation/measurements/README.md`.

    `runs` để notebook hạ số lần đo độ trễ xuống: notebook cần TỶ LỆ ĐÚNG, còn 7 lần chạy là giao
    thức đo ĐỘ TRỄ. Giữ 7 lần trong notebook là chờ 7 lần lâu hơn cho một con số notebook không in.
    """
    lat: dict[tuple[str, str], dict[str, Ketqua]] = {}
    for nhom in ("written", "derived"):
        for dang in ("A", "B", "*"):
            lat[(nhom, dang)] = {k: Ketqua(k) for k in retrievers}

    for case in cases:
        cands = [c for c in theo_doc[case["doc_id"]] if c.chunk_id in set(case["candidates"])]
        if len(cands) != len(case["candidates"]):
            print(f"  ca {case['id']}: ứng viên không khớp kho — bỏ")
            continue
        for ten, kind in retrievers.items():
            times: list[float] = []
            hang: list[str] = []
            for _ in range(runs):
                t0 = time.perf_counter()
                hang = xep_hang(kind, case["doc_id"], cands, case["query"])
                times.append((time.perf_counter() - t0) * 1000)
            ms = statistics.median(times)
            for dang in (case["dang"], "*"):
                lat[(case["nhom"], dang)][ten].them(case, hang, ms)
    return lat


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sealed", action="store_true",
                   help="Chạy trên tập NIÊM PHONG. Mở đúng một lần rồi ghi ngày vào tệp chia.")
    p.add_argument("--chi-tiet", action="store_true", help="In từng ca sai.")
    args = p.parse_args(argv)

    cases, hos, theo_doc = nap(args.sealed)
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8-sig"))

    if args.sealed and not split.get("sealed_opened"):
        print("=" * 78)
        print("MỞ TẬP NIÊM PHONG. Sau lần này con số trên tập đó KHÔNG còn là held-out.")
        print("Ghi ngày mở vào `chunk_selection_split.json` ngay sau khi chạy.")
        print("=" * 78 + "\n")

    retrievers = build_retrievers()
    ten_tap = "NIÊM PHONG" if args.sealed else "PHÁT TRIỂN"
    print(f"CHỌN MỤC TRONG TÀI LIỆU — tập {ten_tap}: {len(cases)} ca / {len(hos)} họ\n")

    # Đo độ trễ theo giao thức release: 7 lần, lấy trung vị.
    lat = do_lat(cases, retrievers, theo_doc)

    def in_lat(nhom: str, tieu_de: str) -> None:
        if not lat[(nhom, "*")][next(iter(retrievers))].n:
            return
        print(tieu_de)
        for dang, nhan in (("*", "cả hai dạng"), ("A", "dạng A — trùng từ khóa"),
                           ("B", "dạng B — diễn đạt khác")):
            print(f"  {nhan}")
            for ten in retrievers:
                print("  " + lat[(nhom, dang)][ten].dong())
        print()

    in_lat("written", "NHÓM `written` — 12 tài liệu, mỗi tài liệu một cấu trúc riêng (SỐ CHÍNH)")
    in_lat("derived", "NHÓM `derived` — khuôn dùng chung, MỘT quyết định lặp (báo cáo RIÊNG)")

    # Kết luận đọc từ số, không viết tay.
    chinh = lat[("written", "*")]
    if len(retrievers) > 1 and chinh[next(iter(retrievers))].n:
        xep = sorted(retrievers, key=lambda t: -statistics.fmean(chinh[t].top1))
        nhat, nhi = xep[0], xep[1]
        d = statistics.fmean(chinh[nhat].top1) - statistics.fmean(chinh[nhi].top1)
        n = chinh[nhat].n
        print(f"Trên nhóm `written`: {nhat} dẫn {nhi} {d:+.3f} Top-1 (n={n}, "
              f"một ca là {1 / n:.3f}).")
        if d < 2.0 / n:
            print(f"  Chênh lệch NHỎ HƠN hai ca. Ở n={n} thì đó không phải căn cứ để đổi hệ thống.")
        # Dạng B là chỗ quyết định: nó là chỗ embedding phải hơn nếu nó hiểu nghĩa.
        b = lat[("written", "B")]
        xep_b = sorted(retrievers, key=lambda t: -statistics.fmean(b[t].top1))
        print(f"  Trên riêng dạng B (diễn đạt khác): {xep_b[0]} dẫn, "
              + ", ".join(f"{t}={statistics.fmean(b[t].top1):.3f}" for t in xep_b))

    if args.chi_tiet:
        for ten in retrievers:
            k = chinh[ten]
            if k.sai:
                print(f"\n{ten} sai {len(k.sai)} ca (nhóm written):")
                for cid, q, dung, hang in k.sai[:12]:
                    print(f"  {cid}  hạng đúng={hang or 'không có'}  {q}")

    # GHI LẠI cho bộ sinh báo cáo đọc. Xem chú thích cùng chủ đề trong
    # `run_retrieval_comparison.py`: báo cáo đồ án đã trôi vì số liệu viết tay.
    #
    # MỘT tệp cho MỖI nhóm split, vì hai nhóm trả lời hai câu hỏi khác nhau — "phát triển" là tập đã
    # sửa theo, "niêm phong" mở đúng một lần. Ghi chung thì lần chạy sau xóa bằng chứng của nhóm kia.
    #
    # KHÔNG ghi khi thiếu embedding. Một lần chạy chỉ có BM25 sẽ ghi đè bằng chứng có cả ba bộ bằng một
    # bản nghèo hơn — và báo cáo sau đó in một bảng so sánh **thiếu hai phương pháp** mà vẫn trông như
    # một bảng đầy đủ. Cùng lỗi đã làm CI đỏ ở bộ so toàn kho: một lần chạy HẸP ghi đè kết quả RỘNG.
    if len(retrievers) < 3:
        print(f"\nKHÔNG ghi bằng chứng: chỉ có {len(retrievers)} bộ ({', '.join(retrievers)}), cần 3.")
        print("  Bằng chứng đã commit rộng hơn lần chạy này, nên ghi đè là làm nó nghèo đi.")
        return 0

    import results

    duong = results.ghi(
        "chon_muc_niem_phong" if args.sealed else "chon_muc_phat_trien",
        {
            "so_ca": len(cases),
            "so_ho": len(hos),
            "nhom": {
                f"{nhom}|{dang}": {
                    ten: {
                        "n": k.n,
                        "top1": statistics.fmean(k.top1) if k.n else None,
                        "mrr": statistics.fmean(k.mrr) if k.n else None,
                        "san_ngau_nhien": (1.0 / statistics.fmean(k.so_ung_vien)) if k.n else None,
                    }
                    for ten, k in lat[(nhom, dang)].items()
                }
                for nhom in ("written", "derived")
                for dang in ("*", "A", "B")
            },
        },
        {
            "ngay": datetime.date.today().isoformat(),
            "tap": "niem_phong" if args.sealed else "phat_trien",
            "bo_da_so": sorted(retrievers),
            "so_lan_do_do_tre": LATENCY_RUNS,
        },
    )
    print(f"\nđã ghi {duong.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
