# -*- coding: utf-8 -*-
"""Golden test đầu-cuối: hỏi như khách thật, qua ĐỦ chuỗi gọi.

    quét QR -> phiên bàn -> phiên chat -> backend .NET -> dịch vụ AI -> mô hình
    -> câu trả lời -> thẻ giỏ gợi ý -> giỏ hàng thật

Ba tập kia dừng ở các chặng khác nhau và **không tập nào bắt được** ba lỗi tìm ra ngày 2026-07-30,
lúc 132/132 ca, 82/82 lượt, 244 test và CI 4/4 đều xanh. Cả ba lỗi có chung tính chất: mọi tên món
và con số trong câu trả lời đều CÓ THẬT trong thực đơn — nên mọi phép kiểm chống bịa đều xanh — mà
khách đọc ra một điều SAI.

Cần stack đang chạy và MỘT mã QR cho MỖI hội thoại (mỗi hội thoại phải là một bàn sạch — xem
phần kiểm mã QR trong `main`):

    export GOLDEN_QR_TOKENS=ma1,ma2,ma3,ma4,ma5
    python ai/evaluation/run_golden_e2e.py
    python ai/evaluation/run_golden_e2e.py --api http://127.0.0.1:5000 --chi-tiet

Phần CHẤM ĐIỂM của bộ này có test riêng chạy được KHÔNG cần stack — `test_golden_e2e.py`. Bộ đo mà
logic chấm sai sẽ báo xanh trên hệ thống đang sai, và đó là kiểu hỏng tệ nhất.

Mã thoát: 0 nếu mọi lượt đạt, 1 nếu có lượt đỏ, 2 nếu KHÔNG gọi được stack.

Mã 2 khác mã 1 có chủ đích: "chưa dựng stack" không phải "hệ thống sai", và trộn hai thứ đó lại là
cách một bộ đo tự vô hiệu hóa — nó sẽ xanh trên máy không có gì chạy.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GOLDEN_PATH = HERE / "golden_e2e.json"
MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"

# Cụm nói lên là ngoài phạm vi. Dùng chung định nghĩa với thước đo một lượt để hai bộ không lệch
# nhau về nghĩa của chữ "từ chối".
REFUSE_PHRASES = ("mình chỉ hỗ trợ", "ngoài phạm vi", "không cung cấp", "mình không hỗ trợ")
NO_DATA_PHRASES = ("chưa có dữ liệu", "chưa có món đó", "thực đơn của nhà hàng chưa có")
CLARIFY_PHRASES = ("cho mình biết", "bạn muốn", "bạn cho mình biết")

SO_TIEN = re.compile(r"\d[\d.,]*")


class KhongGoiDuocStack(RuntimeError):
    """Không nói chuyện được với backend. Khác hoàn toàn với 'hệ thống trả lời sai'."""


class Khach:
    """Một khách quét QR. Gọi ĐÚNG những endpoint mà frontend gọi, không phải đường nội bộ."""

    def __init__(self, api: str, qr_token: str) -> None:
        self.api = api.rstrip("/")
        ts = self._call("/api/table-sessions", "POST", {"qrToken": qr_token})
        self.table_session_id = ts.get("sessionId") or ts.get("id")
        # Giỏ hàng cần TOKEN của phiên bàn, không phải id phiên. Bản đầu của tôi gửi id và nhận
        # 401 `TABLE_SESSION_TOKEN_INVALID` — đúng chuyện bộ này tồn tại để bắt, chỉ có điều lần
        # này nó bắt tôi.
        self.table_session_token = ts.get("tableSessionToken")
        if not self.table_session_id or not self.table_session_token:
            raise KhongGoiDuocStack(f"phiên bàn thiếu id hoặc token: {sorted(ts)}")
        cs = self._call("/api/chat/sessions", "POST", {"tableSessionId": self.table_session_id})
        self.chat_session_id = cs["chatSessionId"]
        self.token = cs["accessToken"]

    def _call(self, path: str, method: str = "GET", body: dict | None = None,
              headers: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.api}{path}", data=data, method=method)
        req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise KhongGoiDuocStack(
                f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:200]}"
            ) from e
        except (urllib.error.URLError, OSError) as e:
            raise KhongGoiDuocStack(f"{method} {path} -> {e}") from e

    def hoi(self, cau: str) -> dict:
        r = self._call(
            f"/api/chat/sessions/{self.chat_session_id}/messages",
            "POST", {"content": cau}, {"X-Chat-Session-Token": self.token},
        )
        return r["message"]

    def them_vao_gio(self, menu_item_id: str, so_luong: int) -> dict:
        # Trường là `delta`, không phải `quantity`: endpoint này CỘNG THÊM vào giỏ, và backend từ
        # chối delta bằng 0 (`CART_DELTA_INVALID`). Bản đầu của tôi gửi `quantity` — backend đọc
        # `Delta` là 0 và trả 400. Cùng lớp lỗi mà cả bộ này tồn tại để bắt: hợp đồng thật khác
        # hợp đồng tôi tưởng, và chỉ có gọi thật mới lộ ra.
        return self._call(
            f"/api/table-sessions/{self.table_session_id}/cart/items",
            "POST", {"menuItemId": menu_item_id, "delta": so_luong},
            {"X-Table-Session-Token": self.table_session_token},
        )

    def xem_gio(self) -> dict:
        return self._call(
            f"/api/table-sessions/{self.table_session_id}/cart", "GET", None,
            {"X-Table-Session-Token": self.table_session_token},
        )


def load_menu() -> list[dict]:
    return json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))["items"]


def suy_ra_kind(text: str, so_the_gio: int) -> str:
    """Đọc dạng đáp án từ những gì KHÁCH nhận được.

    `ChatMessageResponse` chỉ có `Content` và `SuggestedCartActions` — backend KHÔNG chuyển tiếp
    trường `kind` của dịch vụ AI, vì nó không thuộc hợp đồng khách. Nên bộ này phải suy ra, và đó là
    một hạn chế thật: `cases.json` so `kind` trực tiếp và chính xác hơn.

    Suy ra từ SỐ THẺ GIỎ và cụm mở đầu, **không** từ việc đếm tên món trong văn bản. Bản đầu đếm tên
    món và nó đọc sai một câu tri thức: câu ghép đồ uống nhắc "Trà đào cam sả" và "trà sen" trong văn
    xuôi, hai tên món, nên nó bị đọc thành danh sách. Đếm tên món trong văn xuôi không phân biệt được
    "đây là các món tôi gợi ý" với "tôi đang nói VỀ các món này".

    Việc đếm tên món vẫn giữ ở chỗ khác, và ở đó nó đúng: phép kiểm an toàn `forbid_tags_any`. Một
    món hải sản nhắc trong văn xuôi vẫn là món hải sản đã lọt tới mắt khách dị ứng.
    """
    sach = text.lower()
    if any(p in sach for p in REFUSE_PHRASES):
        return "refuse"
    if any(p in sach for p in NO_DATA_PHRASES):
        return "no_data"
    if "mời bạn tham khảo" in sach or "những món này" in sach or so_the_gio >= 2:
        return "list"
    if any(p in sach for p in CLARIFY_PHRASES) and not so_the_gio:
        return "clarify"
    return "fact"


def dong_tien(gia: int) -> str:
    return f"{gia:,}".replace(",", ".") + "đ"


def cham_the_gio(the: list[dict], text: str, by_id: dict, exp: dict) -> list[str]:
    """Bảy bất biến của thẻ giỏ, áp cho MỌI lượt — không lượt nào được miễn.

    Áp cho mọi lượt chứ không khai từng lượt, vì tiêu chí khai lẻ là chỗ sinh ra lượt không được
    kiểm: quên khai một lượt thì lượt đó xanh mà không đo gì. Cùng lý do `answer_metric.py` áp 6
    phép kiểm giỏ cho cả 140 ca.

    Bất biến số 4 là bất biến đáng nhất: **thẻ giỏ phải là món trợ lý VỪA TƯ VẤN**. Ba bất biến
    đầu chỉ nói thẻ giỏ trỏ vào món có thật với giá đúng — chúng vẫn xanh nếu trợ lý tư vấn món A
    rồi bỏ món B vào thẻ. Khách bấm "thêm vào giỏ" là tin rằng nó thêm đúng món vừa được gợi ý.
    """
    do: list[str] = []
    for a in the:
        mid, ten = a.get("menuItemId"), a.get("name")
        # 1. Món phải TỒN TẠI trong thực đơn.
        mon = by_id.get(mid)
        if mon is None:
            do.append(f"GIỎ: thẻ trỏ vào món không có trong thực đơn: {mid!r} ({ten!r})")
            continue
        # 2. Tên trong thẻ phải khớp thực đơn — không phải tên do đâu đó sinh ra.
        if ten != mon["name"]:
            do.append(f"GIỎ: tên thẻ {ten!r} khác tên thực đơn {mon['name']!r}")
        # 3. Giá phải là giá thực đơn.
        if int(a.get("price") or 0) != int(mon["price"]):
            do.append(
                f"GIỎ: giá thẻ {a.get('price')} khác giá thực đơn {mon['price']} "
                f"của {mon['name']}"
            )
        # 4. Món trong thẻ phải là món CÂU TRẢ LỜI VỪA NÊU.
        if mon["name"] not in text:
            do.append(
                f"GIỎ: thẻ có {mon['name']!r} nhưng câu trả lời KHÔNG nêu món đó — "
                "khách bấm thêm vào giỏ là tin nó thêm đúng món vừa được tư vấn"
            )
        # 5. Số lượng phải là số dương.
        if int(a.get("quantity") or 0) < 1:
            do.append(f"GIỎ: số lượng {a.get('quantity')!r} của {mon['name']}")
        # 6. Luôn cần khách xác nhận — AI không tự đặt món.
        if a.get("requiresCustomerConfirmation") is not True:
            do.append(f"GIỎ: {mon['name']} không đòi khách xác nhận")
        # Lý do phải nêu ràng buộc, không được rỗng.
        if not (a.get("reason") or "").strip():
            do.append(f"GIỎ: {mon['name']} không có lý do gợi ý")
        # Nhãn khách nêu cần tránh KHÔNG được có trong thẻ. Chốt an toàn.
        for tag in exp.get("cart_forbid_tags_any", []):
            if tag in mon["tags"]:
                do.append(f"AN TOÀN GIỎ: {mon['name']} mang `{tag}`")

    # 7. Nhánh chưa hiểu câu hỏi thì KHÔNG được gợi ý đặt món.
    if exp.get("no_cart") and the:
        do.append(f"GIỎ: lượt này không được có thẻ, mà có {[a.get('name') for a in the]}")
    return do


def cham_luot(msg: dict, exp: dict, items: list[dict], by_id: dict,
              by_name: dict) -> tuple[list[str], str]:
    text = msg.get("content") or ""
    the = msg.get("suggestedCartActions") or []
    # Món câu trả lời NÊU TÊN — tra bằng tên thực đơn, không đoán. Dùng cho phép kiểm an toàn và
    # đếm số món, KHÔNG dùng để đọc dạng đáp án (xem `suy_ra_kind`).
    neu_ten = [m for m in items if m["name"] in text]
    kind = suy_ra_kind(text, len(the))
    do: list[str] = []

    if exp.get("kind") and kind != exp["kind"]:
        do.append(f"dạng đáp án đọc ra là `{kind}`, cần `{exp['kind']}`")

    if exp.get("min_items") is not None and len(neu_ten) < exp["min_items"]:
        do.append(f"nêu {len(neu_ten)} món, cần ít nhất {exp['min_items']}")

    if exp.get("min_chars") is not None and len(text) < exp["min_chars"]:
        do.append(f"câu trả lời {len(text)} ký tự, cần ít nhất {exp['min_chars']}")

    for tag in exp.get("forbid_tags_any", []):
        xau = [m["name"] for m in neu_ten if tag in m["tags"]]
        if xau:
            do.append(f"AN TOÀN: câu trả lời nêu món mang `{tag}`: {xau}")

    cum = exp.get("must_say_any")
    if cum and not any(c.lower() in text.lower() for c in cum):
        do.append(f"không có cụm nào trong {cum} — câu trả lời không nói ra phạm vi của nó")

    for c in exp.get("must_not_say_any", []):
        if c.lower() in text.lower():
            do.append(f"câu trả lời có cụm {c!r} mà lượt này KHÔNG được có")

    if exp.get("max_price") is not None:
        qua = [f"{m['name']} {dong_tien(m['price'])}" for m in neu_ten
               if m["price"] > exp["max_price"]]
        if qua:
            do.append(f"vượt ngân sách {dong_tien(exp['max_price'])}: {qua}")

    # Cực trị: chốt GIÁ, không chốt món. Có 5 món cùng giá 95.000đ, nên chốt món là chốt vào thứ
    # tự phá hòa của bảng xếp hạng — tiêu chí đó đỏ khi hệ thống hoàn toàn đúng.
    if exp.get("must_name_priciest"):
        cao = max(m["price"] for m in items)
        if dong_tien(cao) not in text:
            do.append(f"phải nêu giá món đắt nhất thực đơn ({dong_tien(cao)})")
    tran = exp.get("must_name_priciest_within")
    if tran is not None:
        trong = [m for m in items if m["price"] <= tran]
        cao = max(m["price"] for m in trong)
        if dong_tien(cao) not in text:
            do.append(
                f"phải nêu giá món đắt nhất trong {dong_tien(tran)} ({dong_tien(cao)}); "
                f"món rẻ nhất là {dong_tien(min(m['price'] for m in trong))}"
            )

    ten_mon = exp.get("must_state_price_of")
    if ten_mon is not None:
        mon = by_name.get(ten_mon)
        if mon is None:
            do.append(f"ca viết sai: thực đơn không có món {ten_mon!r}")
        elif dong_tien(mon["price"]) not in text:
            do.append(f"phải nêu giá thật {dong_tien(mon['price'])} của {ten_mon}")

    # Không tên món nào ngoài thực đơn được xuất hiện như một món của nhà hàng. Kiểm bằng thẻ giỏ
    # và bằng số tiền, hai thứ tra được — không quét tên món tự do, vì cách đó bắt oan.
    if exp.get("no_invented_item_names"):
        gia_that = {m["price"] for m in items}
        so = [int(s.replace(".", "").replace(",", "")) for s in SO_TIEN.findall(text)
              if s.replace(".", "").replace(",", "").isdigit()
              and len(s.replace(".", "").replace(",", "")) >= 4]
        la = [t for t in so if t not in gia_that]
        if la:
            do.append(f"số tiền không phải giá thực đơn: {la}")

    do += cham_the_gio(the, text, by_id, exp)
    return do, kind


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default="http://127.0.0.1:5000", help="gốc URL backend")
    p.add_argument("--chi-tiet", action="store_true", help="in mọi câu trả lời")
    args = p.parse_args(argv)

    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8-sig"))
    items = load_menu()
    by_id = {m["id"]: m for m in items}
    by_name = {m["name"]: m for m in items}
    hoi_thoais = data["conversations"]

    # MỖI hội thoại một mã QR riêng, và bộ này DỪNG nếu không đủ.
    #
    # Không phải chuyện cấu hình cho gọn: backend trả lại phiên chat CŨ cho cùng phiên bàn (đúng
    # thiết kế — khách quét lại QR giữa bữa thì không mất ngữ cảnh). Nên dùng một mã QR cho nhiều
    # hội thoại nghĩa là tất cả chia chung một bộ nhớ, và kết quả KHÔNG ĐỌC ĐƯỢC.
    #
    # Đúng chuyện này đã lừa tôi ngày 2026-07-30: tôi tạo "phiên mới" cho từng câu, thấy hệ thống
    # trả lời sai, và mất một lượt điều tra mới nhận ra ngân sách 45.000đ của lần chạy TRƯỚC còn
    # dính trong bộ nhớ. Nên bộ này không cho phép cấu hình sai đó tồn tại.
    #
    # Mã QR không nằm trong repo: nó là bí mật của bàn và luân chuyển khi đóng phiên.
    tokens = [t.strip() for t in (os.environ.get("GOLDEN_QR_TOKENS") or "").split(",") if t.strip()]
    if len(tokens) < len(hoi_thoais):
        print(
            f"Cần {len(hoi_thoais)} mã QR (mỗi hội thoại một bàn SẠCH), có {len(tokens)}.\n\n"
            "  Vì sao mỗi hội thoại một bàn: backend trả lại phiên chat CŨ cho cùng bàn, nên dùng\n"
            "  chung một bàn là để bộ nhớ hội thoại trước chảy sang hội thoại sau — và lúc đó số\n"
            "  đo được không nói lên điều gì.\n\n"
            "  Lấy mã của các bàn chưa dùng:\n\n"
            "    docker compose -f deploy/docker-compose.yml exec -T postgres \\\n"
            "      psql -U restaurant_user -d restaurant_qr -t \\\n"
            "      -c \"select table_code, qr_token from restaurant_tables order by table_code;\"\n\n"
            "    export GOLDEN_QR_TOKENS=ma1,ma2,ma3,ma4,ma5"
        )
        return 2

    print(f"GOLDEN ĐẦU-CUỐI — {args.api}")
    print(f"  {len(hoi_thoais)} hội thoại / "
          f"{sum(len(c['turns']) for c in hoi_thoais)} lượt, mỗi hội thoại một bàn sạch\n")

    tong = dat = 0
    hong: list[str] = []
    for hoi_thoai, qr in zip(hoi_thoais, tokens):
        try:
            khach = Khach(args.api, qr)
        except KhongGoiDuocStack as e:
            print(f"KHÔNG GỌI ĐƯỢC STACK: {e}")
            print("\n  Dựng stack rồi chạy lại:")
            print("    docker compose -f deploy/docker-compose.yml up -d")
            return 2

        print(f"[{hoi_thoai['id']}]  phiên chat {khach.chat_session_id}")
        for j, turn in enumerate(hoi_thoai["turns"], 1):
            tong += 1
            try:
                msg = khach.hoi(turn["user"])
            except KhongGoiDuocStack as e:
                print(f"  lượt {j}: KHÔNG GỌI ĐƯỢC — {e}")
                return 2
            exp = turn.get("expect", {})
            do, kind = cham_luot(msg, exp, items, by_id, by_name)

            # Bấm THÊM VÀO GIỎ thật. Đây là chặng cuối, và nó kiểm điều mà không mảng JSON nào
            # kiểm được: thẻ giỏ có đi qua được đường xác thực và ràng buộc của backend hay không.
            if exp.get("add_first_cart_item_to_cart"):
                the = msg.get("suggestedCartActions") or []
                if not the:
                    do.append("GIỎ: lượt này phải có thẻ để bấm thêm vào giỏ, mà không có thẻ nào")
                else:
                    a = the[0]
                    try:
                        khach.them_vao_gio(a["menuItemId"], int(a.get("quantity") or 1))
                        gio = khach.xem_gio()
                    except KhongGoiDuocStack as e:
                        do.append(f"GIỎ: thêm vào giỏ thật THẤT BẠI — {e}")
                    else:
                        trong_gio = [i.get("menuItemId") for i in (gio.get("items") or [])]
                        if a["menuItemId"] not in trong_gio:
                            do.append(
                                f"GIỎ: đã gọi thêm {a['name']} nhưng giỏ thật không có "
                                f"({trong_gio})"
                            )
                        else:
                            print(f"    + đã thêm {a['name']} vào giỏ thật, giỏ có "
                                  f"{len(trong_gio)} món")

            if do:
                hong.append(f"{hoi_thoai['id']} lượt {j}: {turn['user']!r}")
                print(f"  [ĐỎ] lượt {j}: {turn['user']}")
                for x in do:
                    print(f"        - {x}")
                print(f"        câu trả lời: {(msg.get('content') or '')[:180]}")
            else:
                dat += 1
                print(f"  [ok]  lượt {j} ({kind}): {turn['user']}")
                if args.chi_tiet:
                    print(f"        {(msg.get('content') or '')[:180]}")
                    the = msg.get("suggestedCartActions") or []
                    if the:
                        print(f"        thẻ giỏ: {[a.get('name') for a in the]}")
        print()

    print(f"  lượt : {tong}")
    print(f"  đạt  : {dat}/{tong}  ({dat / tong * 100:.1f}%)" if tong else "  không lượt nào")
    print(f"  đỏ   : {len(hong)}")
    if hong:
        print("\nlượt đỏ:")
        for h in hong:
            print(f"  {h}")
        return 1
    print("\nMọi lượt đạt qua ĐỦ chuỗi gọi: QR -> backend -> dịch vụ AI -> mô hình -> giỏ hàng.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
