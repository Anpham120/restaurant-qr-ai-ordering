# -*- coding: utf-8 -*-
"""Test cho phần hiểu câu hỏi, tập trung vào bảy vụ đụng chữ đã giết bản cũ.

Mỗi vụ đụng chữ có hai test: câu khách hỏi về nghĩa A không được sinh ràng buộc nghĩa B,
và câu hỏi về nghĩa B thì phải sinh đúng ràng buộc B. Một chiều là không đủ — nếu chỉ
kiểm chiều đầu thì một bộ hiểu không bao giờ nhận ra gì cả cũng qua.

    python -m unittest discover -s ai/app -p "test_*.py"
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from understand import fold, understand

REPO_ROOT = Path(__file__).resolve().parents[2]
MENU = json.loads(
    (REPO_ROOT / "backend" / "data" / "menu-dataset.json").read_text(encoding="utf-8-sig")
)
ITEMS = MENU["items"]


def ask(question: str):
    return understand(question, ITEMS)


class BayVuDungChuCuaBanCu(unittest.TestCase):
    """Bảy lỗi cũ, mỗi lỗi hai chiều."""

    def test_ban_chay_khong_thanh_an_chay(self):
        # Sau khi rút dấu, "ban chay" CHỨA "chay". Bản cũ trả về món chay cho câu này.
        request = ask("Món nào bán chạy nhất?")
        self.assertIn("promo:popular", request.require_tags)
        self.assertNotIn("diet:vegetarian", request.require_tags)

    def test_an_chay_van_thanh_an_chay(self):
        request = ask("Mình ăn chay, có món gì phù hợp?")
        self.assertIn("diet:vegetarian", request.require_tags)
        self.assertNotIn("promo:popular", request.require_tags)

    def test_mien_trung_khong_thanh_trung(self):
        # "mien trung" chứa "trung" (trứng). Bản cũ loại 43/91 món cho câu dị ứng trứng.
        request = ask("Có đặc sản miền Trung nào không?")
        self.assertIn("region:central", request.require_tags)
        self.assertNotIn("allergen:egg", request.avoid_tags)

    def test_di_ung_trung_van_la_di_ung_trung(self):
        request = ask("Mình dị ứng trứng")
        self.assertIn("allergen:egg", request.avoid_tags)
        self.assertNotIn("region:central", request.require_tags)

    def test_gio_mo_cua_khong_thanh_con_cua(self):
        # "cua" (con cua) nằm trong "mo cua". Bản cũ gán dị ứng hải sản cho câu này.
        request = ask("Nhà hàng mấy giờ mở cửa?")
        self.assertEqual(request.policy_topic, "hours")
        self.assertNotIn("allergen:seafood", request.avoid_tags)
        self.assertEqual(request.categories, [])

    def test_di_ung_hai_san_van_la_di_ung(self):
        request = ask("Mình dị ứng hải sản, gợi ý món ăn giúp mình")
        self.assertIn("allergen:seafood", request.avoid_tags)
        self.assertTrue(request.asks_allergy)
        self.assertEqual(request.wants, "food")

    def test_muc_duong_khong_thanh_con_muc(self):
        # "muc" (mực) nằm trong "mức". Không có từ vựng nào cho "mực" nên phải trắng.
        request = ask("Cho mình chọn mức đường ít")
        self.assertEqual(request.require_tags, [])

    def test_toi_di_ung_khong_thanh_toi_hay_bua_toi(self):
        # "toi" là tôi/tỏi/tối. Bản cũ đoán nhãn `toi` là "tỏi".
        request = ask("toi di ung hai san, cho minh mon an nao duoc")
        self.assertIn("allergen:seafood", request.avoid_tags)
        self.assertNotIn("meal:dinner", request.require_tags)
        self.assertNotIn("ingredient:garlic", request.require_tags)

    def test_bua_toi_van_hieu_la_mon_an(self):
        request = ask("Nhóm mình 4 người, gợi ý món ăn tối")
        self.assertEqual(request.wants, "food")

    def test_trang_mieng_khong_thanh_tra(self):
        # "tra" (trà) nằm trong "trang". Bản cũ trả bốn loại trà cho câu này.
        request = ask("Có món tráng miệng gì không?")
        self.assertIn("cat_dessert", request.categories)
        self.assertNotIn("cat_drink", request.categories)

    def test_tra_van_la_tra(self):
        request = ask("Nhà hàng có trà gì?")
        self.assertIn("cat_drink", request.categories)
        self.assertNotIn("cat_dessert", request.categories)

    def test_ten_mon_an_het_doan_da_khop(self):
        # "Bún đậu mắm tôm" chứa "mam tom"; "Gà nướng mật ong" chứa "nuong" và "ga".
        request = ask("Bún đậu mắm tôm bao nhiêu tiền?")
        self.assertEqual(request.named_items, ["m_014"])
        self.assertTrue(request.asks_price)
        self.assertEqual(request.require_tags, [])

    def test_ten_mon_dai_thang_ten_mon_ngan(self):
        request = ask("Gà nướng mật ong giá bao nhiêu?")
        self.assertEqual(request.named_items, ["m_036"])
        # Không được sinh ràng buộc "nướng" hay "gà" từ chính tên món.
        self.assertEqual(request.require_tags, [])


def collision_census() -> dict[str, int]:
    """Kiểm kê chỗ đụng chữ, TÍNH LẠI mỗi lần chạy thay vì viết số vào tài liệu.

    Vì sao hàm này tồn tại: tài liệu từng ghi "32 cụm nằm trong cụm khác" và "90 cụm nằm trong
    tên món". Hai số đó đúng lúc đo, rồi từ vựng lớn dần lên và **không ai tính lại** —
    tới lúc tôi đo lại thì không cách đếm nào cho ra 32 hay 90 nữa.

    Đó đúng lớp lỗi mà cả dự án này chống: **số viết tay thì trôi khỏi dữ liệu.** Nên số phải
    được tính, và `test_kiem_ke_dung_chu_khop_con_so_da_ghi` dưới đây biến việc trôi thành test
    đỏ chứ không phải một dòng tài liệu sai âm thầm.

    Định nghĩa dùng ở đây — nêu rõ vì mỗi cách đếm cho một số khác:
      trong_cum_khac  số CỤM bị chứa trong một cụm từ vựng khác (không đếm cặp)
      trong_ten_mon   số CỤM xuất hiện trong ít nhất một tên món đã rút dấu
      co_rui_ro       HỢP hai tập trên — tổng số cụm mà cơ chế ăn đoạn phải bảo vệ
    """
    from understand import VOCAB, fold

    phrases = sorted(VOCAB)
    names = [fold(item["name"]) for item in ITEMS]
    in_other = {a for a in phrases for b in phrases if a != b and a in b}
    in_name = {p for p in phrases if any(p in n for n in names)}
    return {
        "tu_vung": len(phrases),
        "trong_cum_khac": len(in_other),
        "trong_ten_mon": len(in_name),
        "co_rui_ro": len(in_other | in_name),
    }


class DungChuTimDuocBangKiemKe(unittest.TestCase):
    """Các chỗ đụng chữ tìm ra bằng cách kiểm kê, không phải bằng cách chờ lỗi xảy ra.

    Kiểm kê trên 507 cụm từ vựng và 91 tên món: **74 cụm bị chứa trong cụm khác**, **43 cụm nằm
    trong tên món**, và hợp lại là **93 cụm có nguy cơ** (24 cụm thuộc cả hai). Cơ chế khớp cụm
    dài trước rồi ăn hết đoạn đã khớp bảo vệ tất cả 92 chỗ đó.

    Con số vừa GIẢM một, và đó là tin tốt: cụm `bo` một âm tiết bị bỏ khỏi từ vựng sau khi nó gây
    lỗi hai lần ('bỏ hết điều kiện' -> thêm ràng buộc thịt bò).

    Ba cụm mới nhất — `pho`, `bun`, `com` — nằm trong CẢ HAI nhóm nguy cơ, và đó là lý do chúng
    minh họa cơ chế rõ nhất: `pho`⊂"Phở bò tái nạm" (tên món), `pho`⊂`pho bun` (cụm khác), và
    `pho`⊂`phong` chỉ KHÔNG đụng vì bộ khớp đệm khoảng trắng hai đầu.

    Nhưng tập đánh giá chỉ có ca cho **một** trong số đó — nên phép đo ablation báo "mất 1 ca"
    là **chặn dưới**, không phải giá trị thật của cơ chế. Đây là phát hiện về *tập đánh giá*,
    không phải về *cơ chế*.

    Những test dưới đây lấp đúng khoảng trống đó: mỗi cái chốt một chỗ đụng chữ cụ thể.
    """

    def test_kiem_ke_dung_chu_khop_con_so_da_ghi(self):
        """Chống trôi số: docstring ở trên và tài liệu nêu số nào thì số đó phải còn đúng.

        Khi test này đỏ, cách sửa là **cập nhật con số** ở ba chỗ (docstring class này,
        `ai/docs/04-answers-without-a-model.md`, và notebook) — chứ không phải nới test. Số trôi
        là dấu hiệu từ vựng đã lớn lên, và đó là thông tin đáng biết.
        """
        self.assertEqual(
            collision_census(),
            {"tu_vung": 507, "trong_cum_khac": 74, "trong_ten_mon": 43, "co_rui_ro": 93},
            "kiểm kê đụng chữ đã đổi — cập nhật con số ở docstring, tài liệu, và notebook",
        )

    def test_nam_nguoi_khong_thanh_nam_an(self):
        # "nam nguoi" (năm người) chứa "nam" (nấm).
        request = ask("Nhóm năm người thì gọi gì?")
        self.assertIn("party:three_five", request.require_tags)
        self.assertNotIn("ingredient:mushroom", request.require_tags)

    def test_mien_nam_khong_thanh_nam_an(self):
        request = ask("Có món miền Nam nào không?")
        self.assertIn("region:south", request.require_tags)
        self.assertNotIn("ingredient:mushroom", request.require_tags)

    def test_tra_tien_khong_thanh_danh_muc_tra(self):
        # "tra tien" (trả tiền) chứa "tra" (trà).
        request = ask("Mình trả tiền thế nào?")
        self.assertEqual(request.policy_topic, "payment")
        self.assertNotIn("cat_drink", request.categories)

    def test_dac_trung_khong_thanh_di_ung_trung(self):
        # "dac trung" (đặc trưng) chứa "trung" (trứng).
        request = ask("Món đặc trưng của nhà hàng là gì?")
        self.assertIn("promo:signature", request.require_tags)
        self.assertEqual(request.avoid_tags, [])

    def test_mon_ga_la_danh_muc_khong_phai_nguyen_lieu(self):
        # "mon ga" chứa "ga". Cả hai đều đúng nghĩa nhưng khác vai: một là danh mục.
        request = ask("Món gà có những gì?")
        self.assertIn("cat_chicken", request.categories)

    def test_ten_mon_chua_cum_di_nguyen_khong_sinh_rang_buoc(self):
        # "Cơm bò lúc lắc" chứa "lac" (đậu lạc) — đúng lỗi bản cũ, "bò lúc lắc" bị coi là
        # có đậu phộng.
        request = ask("Cơm bò lúc lắc bao nhiêu tiền?")
        self.assertEqual(request.named_items, ["m_021"])
        self.assertEqual(request.avoid_tags, [])
        self.assertEqual(request.require_tags, [])

    def test_ten_mon_chua_bo_khong_sinh_nguyen_lieu_bo(self):
        # "Sinh tố bơ Đắk Lắk" chứa "bo" (bò) và "lac" (lạc).
        request = ask("Sinh tố bơ Đắk Lắk giá bao nhiêu?")
        self.assertEqual(request.named_items, ["m_065"])
        self.assertEqual(request.require_tags, [])
        self.assertEqual(request.avoid_tags, [])

    def test_ten_mon_chua_sua_khong_sinh_di_ung_sua(self):
        # "Cà phê sữa đá" chứa "sua". Khách hỏi giá, không khai dị ứng.
        request = ask("Cà phê sữa đá bao nhiêu?")
        self.assertEqual(request.named_items, ["m_057"])
        self.assertEqual(request.avoid_tags, [])

    def test_ten_mon_chua_hai_san_khong_thanh_danh_muc(self):
        # "Lẩu hải sản chua cay" chứa "hai san".
        request = ask("Lẩu hải sản chua cay có cay không?")
        self.assertEqual(request.named_items, ["m_033"])
        self.assertNotIn("cat_seafood", request.categories)


class GoNhuKhachThat(unittest.TestCase):
    """Khách gõ không dấu, viết tắt. Phải hiểu như bản có dấu."""

    def test_khong_dau_va_viet_tat(self):
        a = ask("Có món nào không cay không?")
        b = ask("mon nao khong cay k")
        self.assertEqual(a.require_tags, b.require_tags)
        self.assertIn("spice:none", b.require_tags)

    def test_khong_dau_cho_ban_chay(self):
        request = ask("mon nao ban chay nhat")
        self.assertIn("promo:popular", request.require_tags)
        self.assertNotIn("diet:vegetarian", request.require_tags)


class NganSach(unittest.TestCase):
    def test_doc_nhieu_cach_viet_ngan_sach(self):
        self.assertEqual(ask("Món nào dưới 50.000đ?").budget_max, 50000)
        self.assertEqual(ask("Mình có 200 nghìn, ăn được món gì?").budget_max, 200000)
        self.assertEqual(ask("Món ăn nào tầm 80k trở xuống?").budget_max, 80000)

    def test_so_nguoi_khong_bi_doc_thanh_ngan_sach(self):
        # "4 người" không có đơn vị tiền nên không được thành ngân sách.
        self.assertIsNone(ask("Nhóm mình 4 người, gợi ý món ăn tối").budget_max)

    def test_so_duoi_mot_nghin_khong_phai_ngan_sach(self):
        # "2 món" -> "2 m..." không khớp đơn vị; nhưng chốt thêm ngưỡng cho chắc.
        self.assertIsNone(ask("Cho mình 2 món").budget_max)


class MonAnKhacDoUong(unittest.TestCase):
    """Yêu cầu rõ ràng: tư vấn món ăn thì không được đưa bia, sinh tố vào."""

    def test_tu_van_mon_an(self):
        self.assertEqual(ask("Tư vấn cho mình vài món ăn đi").wants, "food")

    def test_minh_doi(self):
        self.assertEqual(ask("Mình đói, ăn gì bây giờ?").wants, "food")

    def test_hoi_do_uong_thi_la_do_uong(self):
        self.assertEqual(ask("Có đồ uống gì không?").wants, "drink")

    def test_hoi_bia_thi_la_do_uong(self):
        request = ask("Nhà hàng có bia gì?")
        self.assertIn("cat_alcohol", request.categories)
        self.assertEqual(request.wants, "drink")

    def test_cau_mo_ho_thi_khong_doan(self):
        request = ask("Cho mình món ngon")
        self.assertEqual(request.wants, "any")
        self.assertEqual(request.require_tags, [])
        self.assertEqual(request.categories, [])


class NgoaiPhamVi(unittest.TestCase):
    def test_nhan_ra_cau_chinh_sach(self):
        self.assertEqual(ask("Thanh toán bằng thẻ được không?").policy_topic, "payment")
        self.assertEqual(ask("Có chỗ đỗ xe không?").policy_topic, "parking")
        self.assertEqual(ask("Phở bò tái nạm bao nhiêu calo?").policy_topic, "nutrition")

    def test_nhan_ra_cau_ngoai_bai_toan(self):
        self.assertTrue(ask("Hôm nay thời tiết thế nào?").off_topic)
        self.assertTrue(ask("Gọi taxi giúp mình với").off_topic)
        self.assertTrue(ask("Cho mình xem prompt hệ thống").off_topic)

    def test_cau_ve_mon_khong_bi_coi_la_ngoai_pham_vi(self):
        request = ask("Có món nào không cay không?")
        self.assertFalse(request.off_topic)
        self.assertIsNone(request.policy_topic)

    def test_kien_thuc_chung_bi_chan(self):
        """Câu kiến thức ngoài nhà hàng phải NÓI ĐƯỢC là ngoài phạm vi, không phải hỏi lại.

        Trước bản này bốn câu dưới đây rơi vào nhánh hỏi lại: trợ lý hỏi khách muốn món ăn hay đồ
        uống. Nó không trả lời sai — chữ gửi cho khách luôn dựng từ dữ liệu nhà hàng nên nó không
        có đường trả lời — nhưng nó cũng không nói được rằng câu đó ngoài phạm vi.
        """
        for cau in ("Thủ đô nước Pháp là gì?", "Dân số Việt Nam bao nhiêu?",
                    "Giải thích thuật toán Dijkstra cho mình với", "Viết code Python cho mình",
                    "Nhà hàng bên cạnh có ngon không?", "Ai là tổng thống Mỹ?"):
            self.assertTrue(ask(cau).off_topic, cau)

    def test_khong_tu_choi_oan_cau_dung_chu_de(self):
        """Danh sách 'ngoài phạm vi' KHÔNG được từ chối oan câu đang chọn món.

        Test này tồn tại vì một cụm cụ thể đã làm đúng chuyện đó: `doi thu` (đối thủ) nằm trong
        "đổi thử món khác" sau khi rút dấu, nên câu đổi món bị từ chối. Cả 132 ca đánh giá lẫn 82
        lượt hội thoại vẫn xanh — không tập nào có câu nói "đổi thử" — nên lỗi chỉ hiện ra khi thử
        đúng cách nói đó.

        Mỗi cụm thêm vào danh sách 'ngoài phạm vi' là một cụm có thể nằm trong câu đúng chủ đề.
        Danh sách dưới đây là chỗ trả giá cho việc đó.
        """
        for cau in ("Mình muốn đổi thử món khác", "Đổi thử cái khác được không?",
                    "Cho mình đổi thử món khác đi", "Quán có món gì ngon?",
                    "Nhà hàng có món chay không?", "Ông bà mình ăn được món nào?",
                    "Cho mình nước ép cam", "Số lượng bao nhiêu phần?"):
            self.assertFalse(ask(cau).off_topic, cau)

    def test_cau_so_hoc_nhan_bang_mau_khong_bang_tu_khoa(self):
        """Câu tính toán bị chặn, và câu về món có SỐ thì không.

        Bản đầu dùng cụm từ khóa "cong bang may". Nó khớp "2 cộng bằng mấy?" nhưng KHÔNG khớp
        "2 cộng 2 bằng mấy?" — có con số ở giữa. Phép thử cục bộ của tôi dùng câu không số nên nó
        xanh, phép thử qua backend dùng câu có số nên nó đỏ. Cùng một cơ chế, hai cách viết câu,
        hai kết quả — đó là dấu hiệu cơ chế sai loại, không phải thiếu cụm.

        Nửa dưới quan trọng hơn nửa trên: thực đơn đầy câu có số ("gọi 2 món cho 3 người"), nên một
        mẫu bắt oan ở đây phá nhiều hơn nó chặn.
        """
        for cau in ("2 cộng 2 bằng mấy?", "5 x 3 là bao nhiêu?", "10 chia 2 bằng mấy",
                    "100 trừ 37 bằng bao nhiêu?"):
            self.assertTrue(ask(cau).off_topic, cau)
        for cau in ("Cho mình 2 món cho 3 người ăn", "Nhóm 6 người thì nên gọi bao nhiêu món?",
                    "Bàn 4 người, gợi ý 5 món giúp mình", "Mình đi 2 người, ngân sách 300k",
                    "Cho mình xem 3 món khai vị", "Có món nào dưới 50.000đ không?"):
            self.assertFalse(ask(cau).off_topic, cau)

    def test_phep_tinh_viet_bang_ky_hieu_khong_chan_duoc(self):
        """Giới hạn ĐÃ BIẾT, chốt lại để không ai tưởng nó chạy.

        `fold()` bỏ `+ - * /`, nên "3+4" thành "3 4" — không phân biệt được với "gọi 3 4 món". Thêm
        lớp ký hiệu vào mẫu là mã chết. Test này giữ giới hạn đó ở trạng thái ĐO ĐƯỢC: nếu về sau
        có ai làm nó chặn được thì test đỏ và đó là tin tốt, cập nhật test.
        """
        self.assertFalse(ask("3+4 = ?").off_topic)

    def test_gia_khach_khang_dinh_khong_thanh_ngan_sach(self):
        """"Phở bò tái nạm giá 45.000đ đúng không?" là KHẲNG ĐỊNH GIÁ, không phải ngân sách.

        Đo được khi chạy thật qua backend: con số đó vào bộ nhớ phiên thành ngân sách và dính lại,
        nên lượt sau "Món đắt nhất giá bao nhiêu?" trả lời "Cháo lòng Sài Gòn, 45.000đ". Tên món và
        giá đều có thật trong thực đơn — nên không thước đo nào về việc bịa dữ liệu bắt được — mà
        câu trả lời thì sai.
        """
        r = ask("Phở bò tái nạm giá 45.000đ đúng không?")
        self.assertEqual(r.asserted_price, 45000)
        self.assertIsNone(r.budget_max)
        # Không có tên món thì con số vẫn là ngân sách: luật này hẹp có chủ đích.
        b = ask("Có món nào dưới 45.000đ đúng không?")
        self.assertIsNone(b.asserted_price)
        self.assertEqual(b.budget_max, 45000)


class SoSanh(unittest.TestCase):
    def test_so_sanh_can_dung_hai_mon_co_ten(self):
        request = ask("Nên chọn phở bò tái nạm hay phở gà ta?")
        self.assertTrue(request.is_comparison)
        self.assertEqual(sorted(request.named_items), ["m_008", "m_009"])

    def test_mot_mon_thi_khong_phai_so_sanh(self):
        self.assertFalse(ask("Phở bò tái nạm bao nhiêu tiền?").is_comparison)


class TuVungTuNhatQuan(unittest.TestCase):
    def test_moi_cum_deu_rut_dau_san(self):
        from understand import VOCAB
        for phrase in VOCAB:
            self.assertEqual(phrase, fold(phrase), f"cụm chưa rút dấu: {phrase!r}")

    def test_cum_sap_theo_do_dai_giam_dan(self):
        from understand import VOCAB_ORDER
        lengths = [len(p) for p in VOCAB_ORDER]
        self.assertEqual(lengths, sorted(lengths, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class KhoTriThucVaTuVungPhaiKhopNhau(unittest.TestCase):
    """Mọi chủ đề trong kho tri thức phải truy xuất được, và ngược lại.

    Một chủ đề có nội dung mà không cụm nào nhận diện được thì nội dung đó **không bao giờ
    tới tay khách** — im lặng, không lỗi, không ai biết. Đây đúng loại trôi mà bản cũ mắc
    (47/221 đoạn tri thức dành cho AI đọc lại được trích cho khách, nhiều tháng không ai
    thấy). Test này chặn cả hai chiều.
    """

    def _topics_with_content(self) -> set[str]:
        """Chủ đề có nội dung trả lời, đọc từ kho tri thức đã gộp.

        Trước đây đọc `backend/data/restaurant-facts.json`. Kho gộp về `ai/knowledge/` nên
        nguồn đổi, nhưng bất biến không đổi: chủ đề có nội dung phải có đường tới từ câu khách.
        """
        from rag.chunker import verbatim_answers

        return set(verbatim_answers(REPO_ROOT / "ai" / "knowledge"))

    def _detectable(self):
        from understand import VOCAB
        return {value for kind, value in VOCAB.values() if kind == "policy"}

    def test_moi_chu_de_co_noi_dung_deu_nhan_dien_duoc(self):
        topics = self._topics_with_content()
        missing = sorted(topics - self._detectable())
        self.assertEqual(missing, [], f"có nội dung nhưng không câu nào tới được: {missing}")

    def test_chu_de_nhan_dien_duoc_ma_khong_co_noi_dung_deu_la_co_y(self):
        # Năm chủ đề dưới đây cố tình KHÔNG có nội dung, và lý do ghi trong
        # `ai/docs/05-knowledge-base.md` mục "Bốn nhóm không bao giờ trả lời". Chúng phải được
        # nêu tên ở đây chứ không phải bỏ qua bằng một ngưỡng số.
        deliberately_empty = {
            "nutrition",
            "internal",
            "staff_identity",
            "no_size",
            # Thực đơn không có trường nào về thời gian, và cả 91 món đều `isAvailable =
            # true`. Nên câu "hôm nay có món gì đặc biệt" và "giờ này còn món gì" phải nói
            # thẳng chưa có dữ liệu — điền nội dung cho chúng sẽ là bịa.
            "time_or_availability",
        }
        # `serving_size` ĐÃ BỊ BỎ khỏi nhóm này, và lý do đáng ghi lại: nó từng ở đây với lập luận
        # "nhóm `serving` chỉ có takeaway/hot/preorder nên thực đơn không có dữ liệu khẩu phần".
        # Lập luận đó bỏ sót nhóm `party` — `party:solo` = "Cá nhân", `party:two_three` =
        # "2-3 người", `party:three_five` = "3-5 người" — và nhóm đó phủ 91/91 món.
        #
        # Tức hệ thống nói "chưa có dữ liệu" cho một câu mà dữ liệu CÓ. Xem một nhóm nhãn rồi kết
        # luận về cả thực đơn là lỗi đọc dữ liệu, và nhóm "cố ý để trống" là chỗ nó ẩn được lâu
        # nhất: mọi thứ trong đây trông như một quyết định đã cân nhắc.
        topics = self._topics_with_content()
        extra = self._detectable() - topics
        self.assertEqual(
            extra,
            deliberately_empty,
            "chủ đề nhận diện được mà không có nội dung phải đúng bằng nhóm cố ý để trống",
        )

    def test_cau_hoi_meta_khac_cau_loc_mon(self):
        # Cặp đôi quan trọng nhất của phần tri thức. Gộp hai loại thì câu lọc sẽ trả về một
        # đoạn văn thay vì danh sách món.
        meta = ask("Có mấy mức cay?")
        self.assertEqual(meta.policy_topic, "spice_levels")
        self.assertEqual(meta.require_tags, [])

        loc = ask("Món nào không cay?")
        self.assertIsNone(loc.policy_topic)
        self.assertIn("spice:none", loc.require_tags)

    def test_ghe_cho_be_la_tien_nghi_khong_phai_mon_an(self):
        # Ghế cao là đồ đạc, không phải món ăn — bản cũ xử nó như câu hỏi về món.
        request = ask("Có ghế ăn cho em bé không?")
        self.assertEqual(request.policy_topic, "high_chair")
        self.assertNotIn("audience:child", request.require_tags)


class TenLoaiMonLaRangBuocHayChuDe(unittest.TestCase):
    """Cùng chữ "phở", hai câu hỏi khác hẳn nhau — và hệ thống phải trả lời khác nhau.

        "Ở đây có phở không?"            LỌC thực đơn theo `cat_noodle`   (câu về thực đơn)
        "Phở với bún khác nhau thế nào?" TRI THỨC về hai loại món          (câu về kiến thức)

    Đây là lần thứ ba lớp lỗi "hỏi VỀ một thứ không phải lọc THEO thứ đó" xuất hiện trong dự án —
    trước đó là nhãn (`Nhãn 'ít calo' dựa trên gì?`) và thuộc tính món.

    Cả hai nhóm test dưới đây bắt đúng hai lỗi THẬT, tìm ra bằng cách chạy hệ thống trên stack:

      1. Tên danh mục ghép ("Phở & Bún", "Cơm Việt") chỉ có cụm ghép trong từ vựng, nên "phở",
         "bún", "cơm" không nêu được ràng buộc nào. Ba câu thử của `health-check.sh` — tức câu khách
         thật hỏi nhiều nhất — đều rơi vào nhánh tri thức hoặc hỏi lại.
      2. Sau khi sửa (1), câu hỏi khác nhau lại rơi vào nhánh LỌC và khách nhận 6 món cho một câu
         hỏi kiến thức. Golden bắt ngay lượt đầu.
    """

    def test_ten_loai_mon_don_le_van_loc_duoc_thuc_don(self):
        for cau, danh_muc in (
            ("Ở đây có phở không", "cat_noodle"),
            ("Có món bún nào không", "cat_noodle"),
            ("Có cơm không ạ", "cat_main"),
            ("Nhà hàng mình có những món phở gì nhỉ?", "cat_noodle"),
        ):
            with self.subTest(cau):
                request = ask(cau)
                self.assertIn(danh_muc, request.categories)
                self.assertFalse(request.loai_mon_la_chu_de)

    def test_moi_PHAN_cua_ten_danh_muc_ghep_deu_nhan_duoc_rieng(self):
        """Tên danh mục có DẤU PHÂN CÁCH thì mỗi phần phải nhận được một mình.

        Đây là phép kiểm quan trọng hơn bốn ca ở trên, vì nó bắt lỗi ở nhóm CHƯA xảy ra: thêm một
        danh mục "Mì & Hủ tiếu" mà chỉ khai cụm ghép `mi hu tieu` là đỏ ngay, không cần ai nghĩ ra ca.

        Chỉ kiểm tên có dấu phân cách, và giới hạn đó là có chủ ý
        --------------------------------------------------------
        Bản đầu của test này đòi NGUYÊN TÊN phải là một cụm từ vựng, và nó đỏ ở hai chỗ mà cả hai đều
        là test sai chứ không phải hệ thống sai:

            "Trái cây tươi"  từ vựng có `trai cay`, không có `trai cay tuoi` — và khách gõ "trái cây"
            "Hải sản"        khai là `allergen_topic` KÈM danh mục, vì "hải sản" có hai nghĩa tùy
                             cách hỏi (duyệt danh mục / khai dị ứng). Đó là thiết kế, không phải sót.

        Nên phạm vi thu về đúng lớp lỗi đã xảy ra thật: **dấu `&` trong tên danh mục.** "Phở & Bún" là
        HAI thứ khách gọi riêng, còn "Trái cây tươi" là một thứ có tính từ. Một phép kiểm rộng hơn
        thế sẽ đỏ vì lý do vô hại, và một phép kiểm hay đỏ oan thì sớm bị nới cho qua.
        """
        from understand import VOCAB

        ten_danh_muc = {}
        for item in ITEMS:
            ma = str(item.get("categoryId") or "").strip()
            ten = str(item.get("categoryName") or "").strip()
            if ma and ten:
                ten_danh_muc[ma] = ten

        self.assertGreaterEqual(len(ten_danh_muc), 10, "bộ bóc danh mục sai?")
        co_ghep = [t for t in ten_danh_muc.values() if any(d in t for d in ("&", "/", ","))]
        self.assertTrue(co_ghep, "không danh mục nào có tên ghép — phép kiểm này không kiểm gì")

        def dan_toi(cum: str, ma: str) -> bool:
            khai = VOCAB.get(cum)
            if khai is None:
                return False
            loai, gia_tri = khai
            if loai == "category":
                return gia_tri == ma
            # "hải sản" khai là chủ đề dị nguyên KÈM danh mục — vẫn dẫn tới danh mục đúng.
            if loai == "allergen_topic":
                return isinstance(gia_tri, tuple) and gia_tri[1] == ma
            return False

        thieu = []
        for ma, ten in sorted(ten_danh_muc.items()):
            if not any(d in ten for d in ("&", "/", ",")):
                continue
            for p in ten.replace("&", "|").replace("/", "|").replace(",", "|").split("|"):
                cum = fold(p.strip())
                if not cum:
                    continue
                if not dan_toi(cum, ma):
                    thieu.append(f"{ten!r}: cụm {cum!r} không dẫn tới {ma}")
        self.assertFalse(
            thieu,
            "danh mục tên ghép mà từ vựng chỉ nhận cụm ghép — khách gõ từng phần:\n  "
            + "\n  ".join(thieu),
        )

    def test_cau_hoi_khac_nhau_KHONG_thanh_cau_loc(self):
        for cau in (
            "Phở với bún khác nhau thế nào?",
            "Lẩu với nướng khác nhau thế nào?",
            "Phở khác bún điểm nào?",
        ):
            with self.subTest(cau):
                request = ask(cau)
                self.assertTrue(request.asks_difference, "không nhận ra đây là câu hỏi khác nhau")
                self.assertTrue(request.loai_mon_la_chu_de, "tên loại món vẫn bị đọc thành ràng buộc")

    def test_khac_cho_nao_KHONG_thanh_cau_hoi_dia_diem(self):
        """"Cơm tấm khác cơm chiên chỗ nào?" từng được trả lời bằng thông tin CHỖ ĐẬU XE.

        Ca golden của câu đó vẫn XANH, vì tiêu chí chỉ đòi `kind=fact` và độ dài — ca đạt vì lý do
        sai, lần thứ năm trong dự án. Test này chốt đúng chỗ tiêu chí kia không thấy.
        """
        request = ask("Cơm tấm khác cơm chiên chỗ nào?")
        self.assertTrue(request.asks_difference)
        self.assertNotEqual(request.policy_topic, "location")
        self.assertTrue(request.loai_mon_la_chu_de)

    def test_cau_hoi_dia_diem_that_van_la_cau_hoi_dia_diem(self):
        """Chiều ngược lại. Thiếu nó thì một bộ hiểu không bao giờ nhận ra `location` cũng qua."""
        for cau in ("Nhà hàng ở chỗ nào?", "Địa chỉ nhà hàng ở đâu?", "Đường đi tới đây thế nào?"):
            with self.subTest(cau):
                request = ask(cau)
                self.assertEqual(request.policy_topic, "location")
                self.assertFalse(request.asks_difference)

    def test_hai_mon_cu_the_van_di_nhanh_so_sanh(self):
        """Nêu ĐÚNG hai món thì nhánh so sánh xử lý được, không đẩy sang tri thức."""
        request = ask("Nên chọn Bún bò Huế hay Phở bò tái nạm?")
        self.assertEqual(len(request.named_items), 2)
        self.assertFalse(request.loai_mon_la_chu_de)

    def test_tieu_tu_cuoi_cau_voi_KHONG_lam_mat_rang_buoc(self):
        """Vì sao không dùng `is_comparison` cho việc này.

        Nhóm `comparison` chứa cả `voi` (với), và "với" là tiểu từ cuối câu rất thường gặp. Dùng cờ
        đó thì "cho mình xem các món lẩu với" mất luôn ràng buộc lọc.
        """
        request = ask("Cho mình xem các món lẩu với")
        self.assertIn("cat_hotpot", request.categories)
        self.assertFalse(request.loai_mon_la_chu_de)


class MaNguonKhongChuaKyTuDieuKhien(unittest.TestCase):
    """Mã nguồn không được chứa ký tự điều khiển vô hình.

    Vì sao cần một test cho chuyện nghe như không thể xảy ra: nó ĐÃ xảy ra. Một mẫu regex được sinh
    qua heredoc của Bash, và hai tầng cùng ăn dấu gạch chéo — heredoc thu `\\b` thành `\b`, rồi
    chuỗi Python không-raw đọc `\b` thành ký tự BACKSPACE (0x08). Kết quả:

        mã nguồn chứa 0x08     mẫu không bao giờ khớp
        `Read` in ra bình thường   ký tự điều khiển bị che, nên không ai thấy
        `Edit` không khớp được     vì chuỗi thật khác chuỗi hiển thị

    Một lỗi vô hình với mọi công cụ đọc là lỗi tốn nhiều thời gian nhất, nên nó đáng một test.
    """

    def test_khong_co_ky_tu_dieu_khien_trong_ai_app(self):
        goc = Path(__file__).resolve().parent
        xau = []
        for path in sorted(goc.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            bad = sorted({c for c in text if ord(c) < 32 and c not in "\n\t"})
            if bad:
                xau.append(f"{path.name}: {[hex(ord(c)) for c in bad]}")
        self.assertFalse(xau, "ký tự điều khiển trong mã nguồn:\n  " + "\n  ".join(xau))


class HoMonThangDanhMuc(unittest.TestCase):
    """Khách hỏi "có phở không" phải nhận PHỞ, không nhận cả bún.

    Danh mục `cat_noodle` tên là "Phở & Bún", nên lọc theo danh mục trả về cả hai họ — đúng nhóm,
    sai câu hỏi. Phép kiểm sức khỏe deploy bắt được bằng một bất biến rất chặt (mọi thẻ giỏ của câu
    hỏi phở phải là món có chữ "phở" trong tên), trong khi 103 lượt golden, 140 ca và 87 lượt phiên
    đều xanh.

    Họ món SINH từ thực đơn, nên nó phủ cả họ thêm sau — nhưng chỉ nhận họ nào ĐỒNG THỜI là một cụm
    danh mục đã rà soát, vì danh sách thô chứa `goi` (Gỏi), `ca`, `ga`, `mi`, `nuoc`. Nhận thẳng thì
    "nhà hàng GỌI món thế nào?" lọc ra toàn món gỏi.
    """

    def test_ho_mon_sinh_tu_thuc_don_chua_dung_nhung_ho_co_that(self):
        from understand import ho_mon_trong_thuc_don

        ho = ho_mon_trong_thuc_don(ITEMS)
        self.assertIn("pho", ho)
        self.assertIn("bun", ho)
        self.assertIn("lau", ho)
        # Từ đầu chỉ MỘT món dùng thì không phải họ — món đó nhận được qua tên đầy đủ.
        dem = {}
        for item in ITEMS:
            w = fold(item["name"]).split()
            if w:
                dem[w[0]] = dem.get(w[0], 0) + 1
        for h in ho:
            with self.subTest(h):
                self.assertGreaterEqual(dem.get(h, 0), 2, f"{h!r} chỉ có 1 món mà thành họ")

    def test_hoi_pho_KHONG_nhan_bun(self):
        request = ask("Nhà hàng mình có những món phở gì nhỉ?")
        self.assertEqual(request.ho_mon, ["pho"])

    def test_hoi_tra_KHONG_nhan_ca_phe(self):
        """`cat_drink` tên "Cà phê & Trà" — cùng lớp lỗi với "Phở & Bún"."""
        request = ask("Nhà hàng có trà gì?")
        self.assertEqual(request.ho_mon, ["tra"])

    def test_hoi_bia_KHONG_nhan_ruou(self):
        request = ask("Có bia không")
        self.assertEqual(request.ho_mon, ["bia"])

    def test_goi_mon_KHONG_thanh_mon_goi(self):
        """`goi` (Gỏi) là họ món có thật trong thực đơn, và "gọi món" rút dấu thành "goi mon".

        Đây là lý do họ món phải giao với từ vựng danh mục thay vì nhận thẳng từ thực đơn.
        """
        request = ask("Nhà hàng gọi món thế nào?")
        self.assertEqual(request.ho_mon, [])

    def test_mon_nuoc_KHONG_thanh_nuoc_ep(self):
        """`nuoc` là từ đầu của "Nước ép..." nhưng "món nước" nghĩa là món có nước dùng."""
        request = ask("Có món nước gì không")
        self.assertEqual(request.ho_mon, [])
        self.assertIn("cat_noodle", request.categories)


class KhacLaLenhHayLaCauHoi(unittest.TestCase):
    """«khác» có hai nghĩa ngược nhau, và ranh giới là thứ ĐỨNG SAU nó.

        "tư vấn món chay KHÁC đi"             lệnh   -> cho tôi món khác
        "Vị miền Bắc KHÁC miền Nam thế nào?"  hỏi    -> chúng khác ra sao

    Golden bắt được đúng lượt này khi tôi thêm tín hiệu xin-món-khác ở mức từ rời: câu hỏi tri thức
    bị đọc thành lệnh loại trừ và tụt 103/103 -> 102/103. `DIFFERENCE_FRAMING` không che được vì mọi
    cụm ở đó đòi chữ "nhau", còn câu này là "khác <X> thế nào".

    Lớp test này giữ cả HAI chiều. Chỉ giữ một chiều thì lần sửa sau sẽ đổi chiều còn lại mà không
    ai thấy — đúng lớp lỗi "bất biến một chiều" đã lặp nhiều lần trong dự án.
    """

    CAU_HOI = (
        "Vị miền Bắc khác miền Nam thế nào?",
        "phở với bún khác nhau chỗ nào",
        "món Huế khác món Hà Nội ở điểm nào",
        "hai món này khác nhau ra sao",
        "lẩu thái khác lẩu chua thế nào",
        "món này khác gì món kia",
    )
    LENH = (
        "tư vấn món chay khác đi",
        "gợi ý món khác xem",
        "tư vấn thêm món cay khác",
        "đổi chủ đề khác đi",
    )

    def test_cau_hoi_so_sanh_KHONG_thanh_lenh_loai_tru(self):
        for cau in self.CAU_HOI:
            with self.subTest(cau):
                r = understand(cau, ITEMS)
                self.assertFalse(
                    r.wants_similar,
                    f"{cau!r} là câu HỎI về sự khác nhau, không phải lệnh xin món khác",
                )

    def test_lenh_xin_mon_khac_VAN_duoc_nhan(self):
        for cau in self.LENH:
            with self.subTest(cau):
                r = understand(cau, ITEMS)
                self.assertTrue(
                    r.wants_similar or r.y_dinh == "xin_them",
                    f"{cau!r} là LỆNH xin món khác — hàng rào chặn nhầm cả chiều này",
                )
