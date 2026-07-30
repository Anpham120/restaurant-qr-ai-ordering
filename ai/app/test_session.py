# -*- coding: utf-8 -*-
"""Test bộ nhớ phiên. Trọng tâm là CHỐT AN TOÀN: dị nguyên khai một lần phải giữ suốt phiên.

Cách viết test ở tệp này: mỗi quy tắc hợp nhất có **hai chiều**, và chiều thứ hai là chiều đòi
quy tắc phải đúng CHỖ NÓ KHÁC hai quy tắc kia. Nếu chỉ kiểm "dị nguyên được nhớ" thì một cách
làm sai — cộng dồn tất cả mọi thứ — cũng qua được; nên phải có test đòi ràng buộc cứng **KHÔNG**
được cộng dồn.

    python -m unittest test_session      # trong ai/app
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from answer import respond, select  # noqa: E402
from session import (  # noqa: E402
    MAX_CONTEXT_TAGS,
    MEMORY_VERSION,
    SessionState,
    merge_into_request,
    rolling_summary,
    session_updates,
    update_state,
)
from understand import understand  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ITEMS = json.loads(
    (REPO_ROOT / "backend" / "data" / "menu-dataset.json").read_text(encoding="utf-8-sig")
)["items"]


def turn(state: SessionState, question: str):
    """Chạy một lượt trọn vẹn: hiểu → hợp nhất → trả lời → ghi bộ nhớ."""
    merged = merge_into_request(understand(question, ITEMS), state)
    reply = respond(merged, ITEMS)
    return merged, reply, update_state(state, merged, reply.items)


class ChotAnToanDiNguyenGiuSuotPhien(unittest.TestCase):
    """Bất biến quan trọng nhất của khâu này. Một ca đỏ ở đây là CHẶN, không phải trừ điểm."""

    def test_di_ung_khai_luot_1_van_bao_ve_o_luot_5(self):
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng hải sản")
        # Bốn lượt sau KHÔNG nhắc lại dị ứng. Đây là chỗ bộ nhớ hỏng sẽ lộ ra.
        for cau in ("Món nào rẻ hơn?", "Cho mình món không cay",
                    "Thêm món tráng miệng đi", "Nhóm mình 4 người thì gọi gì"):
            merged, reply, state = turn(state, cau)
            with self.subTest(cau):
                self.assertIn(
                    "allergen:seafood", merged.avoid_tags,
                    f"{cau!r}: MẤT bảo vệ dị ứng — lượt này không nhắc dị ứng nên nếu bộ nhớ "
                    "quên thì hệ thống mời đúng món khách không ăn được",
                )
                bad = [
                    i for i in reply.items
                    if "allergen:seafood" in next(m for m in ITEMS if m["id"] == i)["tags"]
                ]
                self.assertEqual(bad, [], f"{cau!r}: nêu món mang nhãn hải sản: {bad}")

    def test_khai_di_ung_thu_hai_KHONG_xoa_di_ung_thu_nhat(self):
        """Chiều đòi quy tắc phải là CỘNG DỒN, không phải ghi đè.

        Nếu dị nguyên dùng quy tắc ghi đè như ràng buộc cứng, thì khai sữa ở lượt 2 sẽ xóa hải
        sản của lượt 1 — và test ở trên vẫn xanh vì nó chỉ khai một loại.
        """
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng hải sản")
        merged, _, state = turn(state, "Mình cũng không ăn được sữa")
        self.assertIn("allergen:seafood", merged.avoid_tags)
        self.assertIn("allergen:dairy", merged.avoid_tags)

    def test_di_nguyen_nam_trong_bo_nho_ghi_ra(self):
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng đậu phộng")
        self.assertIn("allergen:peanut", state.avoid_tags)
        self.assertIn("đậu phộng", rolling_summary(state))


class RangBuocCungGhiDeTheoNHOM(unittest.TestCase):
    def test_ngan_sach_moi_THAY_ngan_sach_cu(self):
        state = SessionState()
        merged, _, state = turn(state, "Cho mình món dưới 200 nghìn")
        self.assertEqual(merged.budget_max, 200_000)
        merged, _, state = turn(state, "Rẻ hơn 100 nghìn đi")
        self.assertEqual(
            merged.budget_max, 100_000,
            "ngân sách mới phải THAY ngân sách cũ; cộng dồn thì cái nào thắng là tùy thứ tự áp",
        )

    def test_muc_cay_moi_day_muc_cay_cu_ra(self):
        """Ghi đè theo NHÓM, không theo nhãn — đây là chỗ quy tắc dễ viết sai nhất.

        Giữ cả `spice:none` và `spice:hot` thì phép lọc AND cho kết quả RỖNG, và khách nhận
        "không có món nào phù hợp" cho một yêu cầu hoàn toàn hợp lệ.
        """
        state = SessionState()
        merged, _, state = turn(state, "Cho mình món không cay")
        self.assertIn("spice:none", merged.require_tags)
        merged, reply, state = turn(state, "Thôi cho mình món cay đậm")
        self.assertIn("spice:hot", merged.require_tags)
        self.assertNotIn("spice:none", merged.require_tags)
        self.assertGreater(len(select(merged, ITEMS)), 0, "hai mức cay cùng lúc -> kết quả rỗng")

    def test_rang_buoc_cung_KHONG_cong_don(self):
        """Chiều ngược của test trên: nếu ràng buộc cứng cộng dồn thì hai nhóm khác nhau vẫn
        cùng tồn tại (đúng), nhưng CÙNG nhóm cũng cùng tồn tại (sai)."""
        state = SessionState()
        merged, _, state = turn(state, "Cho mình món không cay")
        merged, _, state = turn(state, "Nhóm mình 4 người")
        # Hai NHÓM khác nhau -> giữ cả hai.
        self.assertIn("spice:none", merged.require_tags)
        self.assertIn("party:three_five", merged.require_tags)


class NguCanhCongVaoNhungCoTRAN(unittest.TestCase):
    def test_ngu_canh_tich_luy_qua_luot(self):
        state = SessionState()
        merged, _, state = turn(state, "Mình đi hẹn hò")
        self.assertTrue(merged.prefer_tags, "câu dịp ăn phải sinh nhãn ngữ cảnh")
        dau = list(merged.prefer_tags)
        merged, _, state = turn(state, "Trời nóng quá")
        self.assertTrue(
            set(dau) & set(merged.prefer_tags),
            "ngữ cảnh lượt trước phải còn — nếu ghi đè thì mất một trong hai dù cả hai đều đúng",
        )

    def test_ngu_canh_khong_phinh_vo_han(self):
        state = SessionState()
        for cau in ("Mình đi hẹn hò", "Trời nóng quá", "Nhóm mình đi ăn sinh nhật",
                    "Trời lạnh rồi", "Mình muốn món chua chua", "Cho mình món đậm đà"):
            _, _, state = turn(state, cau)
        self.assertLessEqual(len(state.context_tags), MAX_CONTEXT_TAGS)

    def test_ngu_canh_KHONG_loai_mon(self):
        """Ngữ cảnh chỉ sắp thứ tự. Nếu nó lọt vào `require_tags` thì câu hẹn hò chỉ còn 1 món.

        Bất biến đúng là **bỏ `prefer_tags` không đổi số món**, không phải "số món bằng 91". Bản
        đầu của test này đòi 91 và đỏ ở 56 — nhưng 56 đến từ `wants='food'` (câu có chữ "món"
        nên hệ thống hiểu khách hỏi món ăn), hoàn toàn đúng. Test sai, không phải mã sai.
        """
        from dataclasses import replace as _replace

        state = SessionState()
        merged, _, state = turn(state, "Mình đi hẹn hò")
        self.assertTrue(merged.prefer_tags, "tiền đề: câu này phải sinh nhãn ngữ cảnh")
        self.assertEqual(
            len(select(merged, ITEMS)),
            len(select(_replace(merged, prefer_tags=[]), ITEMS)),
            "bỏ prefer_tags mà số món đổi -> ngữ cảnh đang LOẠI món, không chỉ sắp thứ tự",
        )


class GhiBoNhoTuBanDaHopNHAT(unittest.TestCase):
    """Nếu ghi từ bản GỐC thay vì bản đã hợp nhất thì bộ nhớ mất dị nguyên ngay lượt sau."""

    def test_ghi_tu_ban_goc_thi_mat_di_nguyen(self):
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng hải sản")
        # Lượt 2 KHÔNG nhắc dị ứng: bản gốc của lượt 2 có avoid_tags rỗng.
        goc = understand("Món nào rẻ hơn?", ITEMS)
        self.assertEqual(goc.avoid_tags, [], "tiền đề của test: bản gốc lượt 2 không có dị nguyên")
        merged = merge_into_request(goc, state)
        sai = update_state(state, goc, [])          # ghi từ bản GỐC — cách làm SAI
        dung = update_state(state, merged, [])      # ghi từ bản đã hợp nhất — cách làm ĐÚNG
        self.assertEqual(sai.avoid_tags, [], "minh họa cách sai: bộ nhớ mất dị nguyên")
        self.assertIn("allergen:seafood", dung.avoid_tags)


class BoNhoBenNgoaiHongThiKHONG_SAP(unittest.TestCase):
    """Bộ nhớ đến từ mạng. Một phiên có dữ liệu hỏng không được làm chết luồng trả lời khách."""

    def test_payload_la_hoac_hong_deu_cho_phien_trong(self):
        for xau in (None, [], "x", 42, {"avoid_tags": "khong-phai-danh-sach"},
                    {"avoid_tags": [1, 2, None]}, {"budget_max": -5}, {"wants": "xyz"},
                    {"turn_count": "nhieu"}):
            with self.subTest(repr(xau)[:40]):
                state = SessionState.from_payload(xau)  # type: ignore[arg-type]
                self.assertIsInstance(state, SessionState)
                self.assertEqual(state.avoid_tags, [])
                self.assertIsNone(state.budget_max)
                self.assertEqual(state.wants, "any")

    def test_chi_nhan_nhan_di_nguyen_vao_avoid(self):
        """`avoid_tags` trong bộ nhớ chỉ chứa nhãn dị nguyên. Nhãn khác lọt vào đây là nguy hiểm
        theo chiều ngược: nó loại món vĩnh viễn khỏi mọi lượt sau mà khách không hề yêu cầu."""
        state = SessionState.from_payload(
            {"avoid_tags": ["allergen:egg", "spice:hot", "khong-co-hai-cham"]}
        )
        self.assertEqual(state.avoid_tags, ["allergen:egg"])

    def test_di_va_ve_giu_nguyen_noi_dung(self):
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng sữa, cho món không cay dưới 150 nghìn")
        lai = SessionState.from_payload(state.to_payload())
        self.assertEqual(lai.avoid_tags, state.avoid_tags)
        self.assertEqual(lai.hard_tags, state.hard_tags)
        self.assertEqual(lai.budget_max, state.budget_max)


class TomTatSinhTATDINH(unittest.TestCase):
    def test_goi_hai_lan_cho_cung_mot_chuoi(self):
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng hải sản, không cay, dưới 200 nghìn")
        self.assertEqual(rolling_summary(state), rolling_summary(state))

    def test_tom_tat_neu_du_moi_rang_buoc_dang_co(self):
        """Tóm tắt THIẾU so với bộ nhớ là nguy hiểm: người đọc log tưởng ràng buộc không tồn tại."""
        state = SessionState()
        _, _, state = turn(state, "Mình dị ứng hải sản, cho món không cay dưới 200 nghìn")
        tom_tat = rolling_summary(state)
        self.assertIn("hải sản", tom_tat)
        self.assertIn("không cay", tom_tat)
        self.assertIn("200.000đ", tom_tat)

    def test_phien_moi_cung_co_tom_tat_doc_duoc(self):
        self.assertIn("Phiên mới", rolling_summary(SessionState()))

    def test_nhan_khong_co_ten_tieng_viet_van_hien_nguyen_nhan(self):
        """Nhãn chưa có tên tiếng Việt phải hiện NGUYÊN NHÃN, không bị bỏ qua.

        So không phân biệt hoa thường, vì chữ đầu câu được viết hoa. Điều test này kiểm là nhãn
        **có mặt**, không phải nó viết hoa hay thường — bỏ qua nhãn mới là lỗi, vì khi đó tóm tắt
        nói THIẾU so với bộ nhớ thật và người đọc log tưởng ràng buộc đó không tồn tại.
        """
        state = SessionState(hard_tags=["season:summer"])
        self.assertIn("season:summer", rolling_summary(state).lower())

    def test_viet_hoa_chu_dau_KHONG_pha_phan_con_lai(self):
        """`str.capitalize()` viết hoa chữ đầu VÀ viết thường tất cả phần còn lại.

        Đó là bug thật đã có trong bản đầu: nó biến `season:summer` thành `Season:summer` — ở đây
        vô hại, nhưng cùng cơ chế sẽ phá tên riêng và nhãn có chữ hoa. Test này chốt rằng chỉ chữ
        đầu bị đổi.
        """
        # Đặt nhãn cần kiểm KHÔNG ở đầu câu, vì chữ đầu câu bị viết hoa theo đúng thiết kế.
        state = SessionState(hard_tags=["spice:none", "region:HCM"])
        tom_tat = rolling_summary(state)
        self.assertIn("region:HCM", tom_tat, "phần sau chữ đầu phải giữ nguyên chữ hoa")
        self.assertTrue(tom_tat[0].isupper(), "chữ đầu câu vẫn phải viết hoa")


class HopDongTraVeChoBackend(unittest.TestCase):
    def test_du_ten_truong_backend_doc(self):
        state = SessionState()
        _, reply, state = turn(state, "Mình dị ứng hải sản, gợi ý món ăn")
        updates = session_updates(state, reply.items)
        for key in ("facts", "constraints", "referenced_menu_item_ids",
                    "suggested_menu_item_ids", "rejected_menu_item_ids",
                    "rolling_summary", "memory_version"):
            self.assertIn(key, updates)
        self.assertEqual(updates["memory_version"], MEMORY_VERSION)

    def test_KHONG_gui_truong_thuoc_quyen_backend(self):
        """`accepted_*` và `added_to_cart_*` là quyền của backend. Không gửi thì ranh giới rõ hơn
        là gửi rồi bị bỏ qua: AI đề xuất, khách xác nhận, backend quyết."""
        updates = session_updates(SessionState(), [])
        self.assertNotIn("accepted_menu_item_ids", updates)
        self.assertNotIn("added_to_cart_menu_item_ids", updates)

    def test_json_hoa_duoc(self):
        state = SessionState()
        _, reply, state = turn(state, "Cho mình món chay dưới 100 nghìn")
        json.dumps(session_updates(state, reply.items), ensure_ascii=False)


class KhongPhaGiDaCo(unittest.TestCase):
    def test_phien_trong_cho_ket_qua_Y_HET_khong_co_phien(self):
        """Bộ nhớ rỗng không được đổi hành vi một lượt. Nếu đổi thì 119 ca hiện có sẽ lệch."""
        for cau in ("Mình dị ứng hải sản, gợi ý món ăn giúp mình", "Phở bò tái nạm bao nhiêu tiền?",
                    "Nhà hàng mấy giờ mở cửa?", "Có món tráng miệng gì không?",
                    "Món nào bán chạy nhất?"):
            with self.subTest(cau):
                goc = respond(understand(cau, ITEMS), ITEMS)
                qua_phien = respond(
                    merge_into_request(understand(cau, ITEMS), SessionState()), ITEMS
                )
                self.assertEqual(goc.text, qua_phien.text)
                self.assertEqual(goc.items, qua_phien.items)
                self.assertEqual(goc.kind, qua_phien.kind)


if __name__ == "__main__":
    unittest.main(verbosity=2)
