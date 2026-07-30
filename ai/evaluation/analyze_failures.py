# -*- coding: utf-8 -*-
"""Truy NGUYÊN NHÂN của mọi ca không đạt, trên cả BA tập đánh giá.

Vì sao là công cụ chứ không phải một mục viết tay trong báo cáo
--------------------------------------------------------------
Yêu cầu "phân tích cả những trường hợp sai cho biết rõ lý do vì sao" viết tay được đúng một lần.
Lần sửa sau thì bảng nguyên nhân trong báo cáo thành sai, và không ai biết. Nên nó là công cụ: nó
đọc trạng thái HIỆN TẠI của hệ thống và in ra chuỗi nguyên nhân truy được về một bước cụ thể.

Ba tập, ba loại "không đạt" khác nhau
------------------------------------
    119 ca trả lời    ĐỎ = câu trả lời không đạt tiêu chí
    138 ca truy hồi   TRƯỢT = không lấy được đoạn đúng · CẤM = lấy phải đoạn bị cấm
    65 lượt phiên     KHOẢNG CÁCH = `aspirational`, hệ thống chưa làm được và tập ca nói ra

Gộp cả ba là cố ý: tập 119 ca hiện **0 đỏ**, nên một công cụ chỉ đọc tập đó sẽ in "không có gì để
phân tích" và người đọc kết luận hệ thống không còn chỗ sai. Thực tế còn hàng chục ca truy hồi
trượt hoặc lấy đoạn lạc đề, và 9 lượt tham chiếu ngược chưa làm được. Che chúng bằng cách chọn tập
là cách dễ nhất để một báo cáo nói dối mà không câu nào sai.

Con số cụ thể KHÔNG viết ở đây, mà do chính công cụ in ra — số viết trong tài liệu thì trôi, và dự
án này đã mắc đúng lỗi đó một lần với con số kiểm kê đụng chữ.

Bảy lớp nguyên nhân, mỗi ca rơi vào ĐÚNG MỘT lớp
------------------------------------------------
    vocab_miss           từ vựng không có cụm khách dùng -> hiểu được 0 ràng buộc
    retrieval_miss       lấy sai đoạn tri thức (hoặc không lấy được đoạn nào)
    constraint_conflict  ràng buộc xung đột -> kết quả rỗng
    data_gap             dữ liệu không có (dinh dưỡng, thời gian nấu, còn hàng, nhãn thiếu)
    criterion_too_strict tiêu chí của CA sai, không phải hệ thống sai
    model_error          mô hình đọc sai ràng buộc
    capability_missing   khả năng CHƯA ĐƯỢC DỰNG — không thiếu từ, không thiếu dữ liệu

Kế hoạch của dự án nêu SÁU lớp. Lớp thứ bảy được thêm vì phép đo chỉ ra nó, và vì gán sai lớp thì
công cụ **chỉ người sau đi sửa sai chỗ**: 9 lượt tham chiếu ngược ("món đầu tiên giá bao nhiêu?")
ban đầu bị xếp `vocab_miss`, nhưng thêm bao nhiêu cụm vào từ vựng cũng không sửa được chúng — hệ
thống không lưu DANH SÁCH CÓ THỨ TỰ các món đã nêu, nên "món đầu tiên" không có gì để trỏ vào.
(`suggested_item_ids` có lưu món, nhưng nó là TẬP dùng để không gợi lại, không phải dãy có thứ tự.)

Lớp `criterion_too_strict` quan trọng nhất và dễ bị bỏ qua nhất: ở dự án này **thước đo sai 3 lần
trước khi hệ thống sai**. Nên công cụ phải nêu được khả năng "ca này viết sai" chứ không mặc định
hệ thống sai. Dấu hiệu nhận ra: nhiều ca đỏ với CÙNG một thông báo.

    python ai/evaluation/analyze_failures.py            # bảng nguyên nhân
    python ai/evaluation/analyze_failures.py --chi-tiet # chuỗi nguyên nhân từng ca
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

import answer  # noqa: E402
import chunk_selectors as CS  # noqa: E402
import run_session_eval as RSE  # noqa: E402
from answer_metric import Answer, score  # noqa: E402
from rag import embedding as EMB  # noqa: E402
from rag.bm25 import Bm25Index  # noqa: E402
from understand import understand  # noqa: E402

CASES_PATH = HERE / "cases.json"
RETRIEVAL_PATH = HERE / "retrieval_cases.json"
MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"

VOCAB_MISS = "vocab_miss"
RETRIEVAL_MISS = "retrieval_miss"
CONSTRAINT_CONFLICT = "constraint_conflict"
DATA_GAP = "data_gap"
CRITERION_TOO_STRICT = "criterion_too_strict"
MODEL_ERROR = "model_error"
CAPABILITY_MISSING = "capability_missing"

MOI_LOP = (
    VOCAB_MISS, RETRIEVAL_MISS, CONSTRAINT_CONFLICT, DATA_GAP,
    CRITERION_TOO_STRICT, MODEL_ERROR, CAPABILITY_MISSING,
)

CACH_SUA = {
    VOCAB_MISS: (
        "Thêm cụm vào `VOCAB` của understand.py — TẤT ĐỊNH. "
        "ĐO ĐƯỢC: nạp từng cụm rồi chạy understand() trên cả tập, giữ cụm nào đổi đúng ca nó nhắm "
        "và không đổi ca nào khác. Đã làm đúng vậy cho 23 cụm ở lần trước."
    ),
    RETRIEVAL_MISS: (
        "Sửa cách xếp hạng, hoặc viết lại đoạn cho tự đủ nghĩa. "
        "ĐO ĐƯỢC: run_retrieval_comparison.py, và chỉ số quyết định là `forbidden@5` chứ không "
        "phải Hit@5 — Hit@5 = 1,0 vẫn đúng khi 1 đoạn đúng đi cùng 4 đoạn lạc đề."
    ),
    CONSTRAINT_CONFLICT: (
        "Nói thẳng 'không có món nào thỏa cả hai điều' — KHÔNG nới ràng buộc. "
        "ĐO ĐƯỢC: run_baseline.py chốt fail-closed, nới là lỗi an toàn."
    ),
    DATA_GAP: (
        "Nói 'tôi chưa có dữ liệu về câu hỏi này' rồi chuyển nhân viên. "
        "KHÔNG ĐO ĐƯỢC bằng dữ liệu hiện có: chỉ chủ nhà hàng bổ sung được. Đây là giới hạn phải "
        "NÓI RA, không phải chỗ để đề xuất sửa."
    ),
    CRITERION_TOO_STRICT: (
        "Sửa TIÊU CHÍ, không sửa hệ thống. "
        "ĐO ĐƯỢC: probe_metric_holes.py + test hai chiều của thước đo. Dấu hiệu: nhiều ca đỏ với "
        "CÙNG một thông báo."
    ),
    MODEL_ERROR: (
        "Chặn ở cổng kiểm nhãn, và đưa cách nói đó về mã tất định. "
        "ĐO ĐƯỢC: run_with_model.py so hai chế độ; mô hình hiện đổi 0 ca nên lớp này đang rỗng."
    ),
    CAPABILITY_MISSING: (
        "DỰNG khả năng đó — ở đây là lưu DÃY CÓ THỨ TỰ các món đã nêu trong `SessionState`, rồi "
        "cho understand.py nhận cụm chỉ vị trí ('món đầu tiên', 'cái thứ ba', 'món vừa rồi'). "
        "ĐO ĐƯỢC: 9 lượt `aspirational` của nhóm `context_reference` chuyển từ khoảng cách sang "
        "đạt, mà `allergy_persists` 25/25 không tụt. "
        "KHÔNG phải vocab_miss: thêm bao nhiêu cụm cũng không sửa được, vì không có gì để trỏ vào."
    ),
}


@dataclass
class Nguyennhan:
    tap: str
    ca: str
    cau: str
    lop: str
    chuoi: list[str] = field(default_factory=list)


def load_menu() -> list[dict]:
    return json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))["items"]


# ------------------------------------------------------- tập 1: 119 ca trả lời
def _hieu_duoc_gi(r) -> list[str]:
    co = []
    if r.require_tags:
        co.append(f"require={r.require_tags}")
    if r.prefer_tags:
        co.append(f"prefer={r.prefer_tags}")
    if r.avoid_tags:
        co.append(f"avoid={r.avoid_tags}")
    if r.categories:
        co.append(f"categories={r.categories}")
    if r.budget_max is not None:
        co.append(f"budget={r.budget_max}")
    if r.policy_topic:
        co.append(f"policy={r.policy_topic}")
    if r.named_items:
        co.append(f"named={r.named_items}")
    return co


def phan_tich_tra_loi(items: list[dict]) -> list[Nguyennhan]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))
    cases = data["cases"]
    menu = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
    ra: list[Nguyennhan] = []
    for c in cases:
        r = understand(c["question"], items)
        reply = answer.respond(r, items)
        v = score(c, Answer(text=reply.text, items=reply.items, kind=reply.kind,
                            asks_back=reply.asks_back), menu, data["named_selectors"])
        if v.passed:
            continue
        hieu = _hieu_duoc_gi(r)
        chuoi = [
            f"hiểu   : {' '.join(hieu) if hieu else 'KHÔNG hiểu gì'}",
            f"nhánh  : {reply.branch}",
            f"đỏ     : {'; '.join(v.reasons)}",
        ]
        if not hieu:
            lop = VOCAB_MISS
        elif reply.branch.startswith("policy:") or "chưa có dữ liệu" in reply.text:
            lop = DATA_GAP
        elif not reply.items and (r.require_tags or r.avoid_tags):
            lop = CONSTRAINT_CONFLICT
        else:
            lop = CRITERION_TOO_STRICT
        ra.append(Nguyennhan("119 ca trả lời", c["id"], c["question"], lop, chuoi))
    return ra


# ------------------------------------------------------ tập 2: 138 ca truy hồi
def bo_truy_hoi_tot_nhat() -> tuple[object, str]:
    """Bộ truy hồi TỐT NHẤT có mặt, kèm tên để in ra.

    Phân tích nguyên nhân bằng bộ KÉM nhất là phóng đại số ca sai: trên 40 ca niêm phong, BM25 đạt
    Hit@5 0,711 còn embedding 0,921. Một bảng nguyên nhân đếm ca trượt của BM25 rồi không nói ra
    mình dùng BM25 sẽ báo hệ thống yếu hơn thực tế.

    Ngược lại, thiếu thư viện thì phải chạy tiếp bằng BM25 và **in rõ** — không bỏ qua âm thầm.
    """
    chunks = CS.corpus()
    bm25 = Bm25Index.build(chunks)
    if not EMB.available():
        return bm25, f"bm25 (embedding không có: {EMB.why_unavailable()})"
    emb = EMB.EmbeddingIndex.build(chunks)
    return emb, "embedding (bộ tốt nhất trên tập niêm phong: Hit@5 0,921 so với bm25 0,711)"


def phan_tich_truy_hoi(index, ten_bo: str) -> list[Nguyennhan]:
    cases = json.loads(RETRIEVAL_PATH.read_text(encoding="utf-8-sig"))["cases"]
    ra: list[Nguyennhan] = []
    for c in cases:
        dung = CS.select_many(c["expected"]) if c["expected"] else set()
        cam = CS.select_many(c["forbidden"]) if c["forbidden"] else set()
        lay = [h.chunk_id for h in index.search(c["query"], k=5)]

        pham_cam = cam & set(lay)
        truot = bool(dung) and not (dung & set(lay))
        if not pham_cam and not truot:
            continue

        chuoi = [f"lấy    : {lay or 'KHÔNG đoạn nào'}"]
        if pham_cam:
            chuoi.append(f"CẤM    : {sorted(pham_cam)} — lạc chủ đề, mô hình có thể viết sai từ đó")
        if truot:
            chuoi.append(f"trượt  : cần một trong {len(dung)} đoạn, không có đoạn nào trong 5 đầu")

        # Câu hỏi không chung TỪ nào với đoạn đúng thì đây là giới hạn của phép trùng từ, không
        # phải lỗi xếp hạng. Phân biệt hai thứ này là điều bảng nguyên nhân phải làm được.
        if truot and not lay:
            chuoi.append(f"chú ý  : {ten_bo.split()[0]} trả RỖNG — không chung từ nào với kho")
        ra.append(Nguyennhan("138 ca truy hồi", c["id"], c["query"], RETRIEVAL_MISS, chuoi))
    return ra


# ------------------------------------------------------ tập 3: 65 lượt phiên
def phan_tich_phien(items: list[dict]) -> list[Nguyennhan]:
    data = json.loads(RSE.SCRIPTS_PATH.read_text(encoding="utf-8-sig"))
    ra: list[Nguyennhan] = []
    for s in data["scripts"]:
        ghi = RSE.chay_kich_ban(s, items)
        for j, bg in enumerate(ghi):
            do = RSE.cham_luot(bg, ghi[:j])
            if not do:
                continue
            asp = bool(bg["expect"].get("aspirational"))
            chuoi = [
                f"lượt   : {j + 1}/{len(ghi)} trong {s['id']}",
                f"hiểu   : {' '.join(_hieu_duoc_gi(bg['request'])) or 'KHÔNG hiểu gì'}",
                f"nhánh  : {bg['reply'].branch}",
                f"{'khoảng cách' if asp else 'đỏ':7}: {'; '.join(do)}",
            ]
            # Lượt tham chiếu ngược thiếu ĐÚNG một thứ: hệ thống không lưu THỨ TỰ món đã nêu, nên
            # "món đầu tiên" không trỏ vào đâu được. `suggested_item_ids` có lưu món, nhưng nó là
            # TẬP dùng để không gợi lại — không phải danh sách có thứ tự để tham chiếu.
            #
            # Đây là `capability_missing`, KHÔNG phải `vocab_miss` — và phân biệt hai lớp này là
            # việc chính của công cụ. Bản đầu xếp chúng vào `vocab_miss`, tức chỉ người sau đi thêm
            # cụm vào từ vựng: một việc không thể sửa được ca nào trong 9 ca này.
            lop = CAPABILITY_MISSING if asp else CONSTRAINT_CONFLICT
            ra.append(Nguyennhan("65 lượt phiên", f"{s['id']}#{j + 1}", bg["user"], lop, chuoi))
    return ra


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chi-tiet", action="store_true", help="In chuỗi nguyên nhân từng ca.")
    args = p.parse_args(argv)

    items = load_menu()
    bo, ten_bo = bo_truy_hoi_tot_nhat()

    tat_ca = (
        phan_tich_tra_loi(items)
        + phan_tich_truy_hoi(bo, ten_bo)
        + phan_tich_phien(items)
    )

    print("PHÂN TÍCH NGUYÊN NHÂN — cả ba tập đánh giá\n")
    print(f"  bộ truy hồi dùng để phân tích: {ten_bo}\n")
    theo_tap = collections.Counter(n.tap for n in tat_ca)
    tong = {"119 ca trả lời": 119, "138 ca truy hồi": 138, "65 lượt phiên": 65}
    print(f"  {'tập':20}{'không đạt':>11}{'tổng':>7}")
    print("  " + "-" * 40)
    for tap, t in tong.items():
        print(f"  {tap:20}{theo_tap.get(tap, 0):>11}{t:>7}")

    print(f"\n  {'lớp nguyên nhân':22}{'ca':>4}   ví dụ")
    print("  " + "-" * 76)
    theo_lop = collections.defaultdict(list)
    for n in tat_ca:
        theo_lop[n.lop].append(n)
    for lop in MOI_LOP:
        ns = theo_lop.get(lop, [])
        vd = f"{ns[0].ca} — {ns[0].cau[:38]}" if ns else "(rỗng)"
        print(f"  {lop:22}{len(ns):>4}   {vd}")

    print("\n  Cách sửa từng lớp, và cách sửa đó có ĐO ĐƯỢC không:")
    for lop in MOI_LOP:
        if not theo_lop.get(lop):
            continue
        print(f"\n    {lop} ({len(theo_lop[lop])} ca)")
        for dong in CACH_SUA[lop].split(". "):
            if dong.strip():
                print(f"      {dong.strip().rstrip('.')}.")

    # Dấu hiệu tiêu chí sai: nhiều ca cùng một thông báo. Đây là chỗ dự án đã sai 3 lần.
    thong_bao = collections.Counter(
        d.split(":", 1)[-1].strip()[:60] for n in tat_ca for d in n.chuoi if d.startswith("đỏ")
    )
    lap = [(m, c) for m, c in thong_bao.most_common() if c >= 3]
    if lap:
        print("\n  CẢNH BÁO — nhiều ca đỏ với CÙNG thông báo, khả năng TIÊU CHÍ sai:")
        for m, c in lap:
            print(f"    {c:>3} ca: {m}")

    if args.chi_tiet:
        print("\n\nCHUỖI NGUYÊN NHÂN TỪNG CA")
        for n in tat_ca:
            print(f"\n  [{n.lop}] {n.ca}  {n.cau!r}")
            for d in n.chuoi:
                print(f"      {d}")
            print(f"      SỬA   : {CACH_SUA[n.lop].split('.')[0]}.")

    print(f"\n  Tổng {len(tat_ca)} ca không đạt trên 322 ca/lượt của cả ba tập.")
    print("  Công cụ này KHÔNG trả mã lỗi: nó phân tích, còn việc CHẶN thuộc run_baseline.py,")
    print("  run_session_eval.py và run_retrieval_comparison.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
