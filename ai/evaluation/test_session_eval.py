# -*- coding: utf-8 -*-
"""Test HAI CHIỀU cho bộ chạy kịch bản đa lượt.

Vì sao phải hai chiều
---------------------
Một bộ chấm chỉ chạy đúng một chiều thì vô dụng: "kịch bản thật đều xanh" cũng đúng với một bộ
chấm **luôn trả về xanh**. Nên mỗi tiêu chí cần hai test:

    chiều thuận   hệ thống đúng -> lượt XANH
    chiều nghịch  hệ thống HỎNG -> lượt ĐỎ, và đỏ vì ĐÚNG lý do

Chiều nghịch là chiều đáng viết. Bộ chấm ở đây tồn tại để bắt "bộ nhớ quên dị nguyên", nên phải
có test dựng ra một bộ nhớ ĐÃ quên rồi kiểm rằng bộ chấm bắt được.

Bài học đã trả giá ở dự án này: thước đo sai **3 lần** trước khi hệ thống sai. Một tiêu chí luôn
xanh không báo lỗi, nó chỉ lặng lẽ nói mọi thứ ổn.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

import run_session_eval as R  # noqa: E402
import session as S  # noqa: E402
from answer import Reply  # noqa: E402
from understand import Request, understand  # noqa: E402

ITEMS = R.load_menu()
THEO_ID = {i["id"]: i for i in ITEMS}


def mon_co_nhan(tag: str) -> dict:
    for i in ITEMS:
        if tag in i["tags"]:
            return i
    raise AssertionError(f"thực đơn không có món nào mang {tag}")


def ban_ghi(
    *,
    expect: dict,
    items: list[dict] | None = None,
    state: S.SessionState | None = None,
    kind: str = "list",
    text: str = "",
    request: Request | None = None,
) -> dict:
    items = items or []
    return {
        "user": "câu thử",
        "expect": expect,
        "request": request or understand("câu thử", ITEMS),
        "reply": Reply(text=text, items=[i["id"] for i in items], kind=kind),
        "state": state or S.SessionState(),
        "items": items,
    }


class BoChamBatDuocLoiAnToan(unittest.TestCase):
    """Chiều nghịch quan trọng nhất: bộ nhớ quên dị nguyên phải bị bắt."""

    def test_bo_nho_quen_di_nguyen_thi_DO(self):
        do = R.cham_luot(
            ban_ghi(
                expect={"memory_must_have_avoid": ["allergen:seafood"]},
                state=S.SessionState(avoid_tags=[]),   # ĐÃ QUÊN
            ),
            truoc=[],
        )
        self.assertEqual(len(do), 1, do)
        self.assertTrue(do[0].startswith("AN TOÀN"), do[0])
        self.assertIn("MẤT", do[0])

    def test_bo_nho_con_di_nguyen_thi_XANH(self):
        do = R.cham_luot(
            ban_ghi(
                expect={"memory_must_have_avoid": ["allergen:seafood"]},
                state=S.SessionState(avoid_tags=["allergen:seafood"]),
            ),
            truoc=[],
        )
        self.assertEqual(do, [])

    def test_cau_tra_loi_co_mon_bi_cam_thi_DO(self):
        mon = mon_co_nhan("allergen:seafood")
        do = R.cham_luot(
            ban_ghi(
                expect={"forbid_tags_any": ["allergen:seafood"]},
                items=[mon],
                state=S.SessionState(avoid_tags=["allergen:seafood"]),
            ),
            truoc=[],
        )
        self.assertEqual(len(do), 1, do)
        self.assertTrue(do[0].startswith("AN TOÀN"), do[0])
        self.assertIn(mon["name"], do[0])

    def test_quen_bo_nho_MA_cau_tra_loi_tinh_co_sach_van_bi_bat(self):
        """Đây là lý do mỗi lượt kiểm HAI thứ chứ không một.

        Hệ thống quên dị ứng, nhưng lượt này khách hỏi món tráng miệng nên câu trả lời tình cờ
        không có món hải sản. Bộ chấm chỉ xem câu trả lời sẽ cho XANH — và lỗi sẽ nổ ở một lượt
        khác, ngẫu nhiên, khó truy. Kiểm cả bộ nhớ biến nó thành lỗi tất định.
        """
        sach = [i for i in ITEMS if "allergen:seafood" not in i["tags"]][:3]
        exp = {
            "forbid_tags_any": ["allergen:seafood"],
            "memory_must_have_avoid": ["allergen:seafood"],
        }
        do = R.cham_luot(
            ban_ghi(expect=exp, items=sach, state=S.SessionState(avoid_tags=[])),
            truoc=[],
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("bộ nhớ MẤT", do[0])
        # Và chỉ kiểm câu trả lời thì nó XANH — chứng minh chiều thứ hai là chiều cần thiết.
        chi_cau_tra_loi = R.cham_luot(
            ban_ghi(
                expect={"forbid_tags_any": ["allergen:seafood"]},
                items=sach,
                state=S.SessionState(avoid_tags=[]),
            ),
            truoc=[],
        )
        self.assertEqual(chi_cau_tra_loi, [])


class BoChamBatDuocLoiGhiDe(unittest.TestCase):
    def test_con_giu_nhan_cu_cung_nhom_thi_DO(self):
        do = R.cham_luot(
            ban_ghi(
                expect={"memory_must_not_have_require": ["spice:none"]},
                state=S.SessionState(hard_tags=["spice:none", "spice:hot"]),
            ),
            truoc=[],
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("CÒN GIỮ", do[0])

    def test_ghi_de_dung_thi_XANH(self):
        do = R.cham_luot(
            ban_ghi(
                expect={
                    "memory_must_have_require": ["spice:hot"],
                    "memory_must_not_have_require": ["spice:none"],
                },
                state=S.SessionState(hard_tags=["spice:hot"]),
            ),
            truoc=[],
        )
        self.assertEqual(do, [])

    def test_ngan_sach_sai_thi_DO(self):
        do = R.cham_luot(
            ban_ghi(
                expect={"memory_budget_max": 100_000},
                state=S.SessionState(budget_max=200_000),
            ),
            truoc=[],
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("200000", do[0].replace(".", ""))


class BoChamBatDuocLoiThamChieuNguoc(unittest.TestCase):
    def test_khong_nhac_mon_luot_truoc_thi_DO(self):
        truoc = [ban_ghi(expect={}, items=[THEO_ID["m_008"]])]
        do = R.cham_luot(
            ban_ghi(expect={"refers_to_turn": 1}, text="Bạn muốn món gì?"),
            truoc=truoc,
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("tham chiếu ngược", do[0])

    def test_nhac_dung_mon_luot_truoc_thi_XANH(self):
        mon = THEO_ID["m_008"]
        truoc = [ban_ghi(expect={}, items=[mon])]
        do = R.cham_luot(
            ban_ghi(expect={"refers_to_turn": 1}, text=f"{mon['name']} giá 89.000đ"),
            truoc=truoc,
        )
        self.assertEqual(do, [])

    def test_neu_lai_dung_danh_sach_cu_thi_DO(self):
        """`must_not_repeat_turn` phải bắt việc liệt kê lại y nguyên.

        Chiều này có thật: một bản tiêu chí trước đây chỉ đòi "nhắc tên món lượt trước", và hệ
        thống ĐẠT bằng cách in lại đúng danh sách cũ — đạt mà không hiểu chữ "giống vậy" nào.
        """
        cu = [THEO_ID["m_008"], THEO_ID["m_009"]]
        truoc = [ban_ghi(expect={}, items=cu)]
        do = R.cham_luot(
            ban_ghi(expect={"must_not_repeat_turn": 1}, items=cu),
            truoc=truoc,
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("không món nào mới", do[0])

    def test_mon_moi_khong_thoa_rang_buoc_luot_truoc_thi_DO(self):
        """Tiêu chí "chung một nhãn bất kỳ" quá lỏng, nên nó đã bị thay.

        `season:all_year` gắn cho 69/91 món, nên hai món bất kỳ gần như luôn chung một nhãn — và
        ca vẫn đạt sai lý do. Tiêu chí hiện tại đòi thỏa đúng RÀNG BUỘC của lượt được trỏ.
        """
        rb_chay = understand("Cho mình món chay", ITEMS)
        self.assertTrue(rb_chay.categories or rb_chay.require_tags, "ca thử phải có ràng buộc")
        truoc = [ban_ghi(expect={}, items=[THEO_ID["m_008"]], request=rb_chay)]
        khong_chay = [
            i for i in ITEMS
            if (rb_chay.categories and i["categoryId"] not in rb_chay.categories)
            or any(t not in i["tags"] for t in rb_chay.require_tags)
        ][:2]
        do = R.cham_luot(
            ban_ghi(expect={"must_match_turn_constraint": 1}, items=khong_chay),
            truoc=truoc,
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("KHÔNG thỏa ràng buộc", do[0])

    def test_luot_truoc_khong_co_rang_buoc_thi_bao_KHONG_DO_DUOC(self):
        """Tiêu chí không đo được gì phải NÓI RA, không được im lặng cho xanh."""
        truoc = [ban_ghi(expect={}, items=[THEO_ID["m_008"]], request=Request(text="", folded=""))]
        do = R.cham_luot(
            ban_ghi(expect={"must_match_turn_constraint": 1}, items=[THEO_ID["m_009"]]),
            truoc=truoc,
        )
        self.assertEqual(len(do), 1, do)
        self.assertIn("không đo được gì", do[0])


class BoKiemTieuChiBatDuocCaLuonXanh(unittest.TestCase):
    """`_kiem_tieu_chi` chặn hai kiểu ca luôn xanh — cả hai đều đã xảy ra thật."""

    def test_luot_chi_co_why_bi_CHAN(self):
        loi = R._kiem_tieu_chi({"id": "x", "turns": [{"user": "a", "expect": {"why": "..."}}]})
        self.assertEqual(len(loi), 1, loi)
        self.assertIn("không có tiêu chí nào ĐO ĐƯỢC", loi[0])

    def test_luot_chi_co_aspirational_bi_CHAN(self):
        loi = R._kiem_tieu_chi({
            "id": "x",
            "turns": [{"user": "a", "expect": {"aspirational": True, "why": "..."}}],
        })
        self.assertEqual(len(loi), 1, loi)
        self.assertIn("`aspirational` nói ca ĐƯỢC PHÉP đỏ", loi[0])

    def test_khoa_expect_viet_sai_ten_bi_CHAN(self):
        loi = R._kiem_tieu_chi({
            "id": "x",
            "turns": [{"user": "a", "expect": {"memory_must_have_avoids": ["x"], "why": "..."}}],
        })
        self.assertTrue(any("không hiểu" in l for l in loi), loi)

    def test_tham_chieu_ve_luot_chua_xay_ra_bi_CHAN(self):
        loi = R._kiem_tieu_chi({
            "id": "x",
            "turns": [{"user": "a", "expect": {"refers_to_turn": 1, "why": "..."}}],
        })
        self.assertEqual(len(loi), 1, loi)
        self.assertIn("lượt TRƯỚC đó", loi[0])

    def test_tap_kich_ban_that_KHONG_co_loi_tieu_chi(self):
        data = json.loads(R.SCRIPTS_PATH.read_text(encoding="utf-8-sig"))
        loi = [l for s in data["scripts"] for l in R._kiem_tieu_chi(s)]
        self.assertEqual(loi, [], f"{len(loi)} tiêu chí viết sai trong tập thật")


class TapKichBanGiuDungHinhDang(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(R.SCRIPTS_PATH.read_text(encoding="utf-8-sig"))
        self.scripts = self.data["scripts"]

    def test_nhom_chot_an_toan_co_kich_ban(self):
        """Nhóm chốt rỗng thì nó không chặn gì — và bảng kết quả vẫn trông đầy đủ."""
        for nhom in R.GATE_GROUPS:
            with self.subTest(nhom):
                self.assertTrue(
                    [s for s in self.scripts if s["group"] == nhom],
                    f"nhóm chốt {nhom} không có kịch bản nào",
                )

    def test_moi_kich_ban_chot_co_luot_KHONG_nhac_di_ung(self):
        """Kịch bản mà mọi lượt đều nhắc dị ứng thì nó không đo bộ nhớ, nó đo phép hiểu câu."""
        for s in self.scripts:
            if s["group"] not in R.GATE_GROUPS:
                continue
            with self.subTest(s["id"]):
                sau = s["turns"][1:]
                self.assertTrue(sau, "kịch bản chốt phải có nhiều hơn một lượt")
                khong_nhac = [
                    t for t in sau
                    if not any(k in t["user"].lower() for k in ("dị ứng", "không ăn", "sữa", "tôm"))
                ]
                self.assertTrue(
                    khong_nhac,
                    "mọi lượt sau đều nhắc dị ứng — kịch bản này không đo bộ nhớ",
                )

    def test_moi_luot_chot_kiem_CA_cau_tra_loi_VA_bo_nho(self):
        for s in self.scripts:
            if s["group"] not in R.GATE_GROUPS:
                continue
            for j, t in enumerate(s["turns"], 1):
                with self.subTest(f"{s['id']} lượt {j}"):
                    self.assertIn("forbid_tags_any", t["expect"])
                    self.assertIn("memory_must_have_avoid", t["expect"])

    def test_luot_aspirational_deu_co_tieu_chi_do_duoc(self):
        for s in self.scripts:
            for j, t in enumerate(s["turns"], 1):
                if not t["expect"].get("aspirational"):
                    continue
                with self.subTest(f"{s['id']} lượt {j}"):
                    self.assertTrue(
                        set(t["expect"]) - R.KHOA_KHONG_DO,
                        "lượt aspirational không có tiêu chí nào — nó sẽ luôn qua",
                    )


class ChayThatTapKichBan(unittest.TestCase):
    """Chốt kết quả: chạy hết tập thật và đòi 0 lỗi an toàn."""

    def test_khong_luot_nao_co_loi_an_toan(self):
        data = json.loads(R.SCRIPTS_PATH.read_text(encoding="utf-8-sig"))
        an_toan: list[str] = []
        for s in data["scripts"]:
            ghi = R.chay_kich_ban(s, ITEMS)
            for j, bg in enumerate(ghi):
                for d in R.cham_luot(bg, ghi[:j]):
                    if d.startswith("AN TOÀN"):
                        an_toan.append(f"{s['id']} lượt {j + 1}: {d}")
        self.assertEqual(an_toan, [], f"{len(an_toan)} lỗi an toàn")

    def test_nhom_chot_khong_luot_nao_do(self):
        data = json.loads(R.SCRIPTS_PATH.read_text(encoding="utf-8-sig"))
        do: list[str] = []
        for s in data["scripts"]:
            if s["group"] not in R.GATE_GROUPS:
                continue
            ghi = R.chay_kich_ban(s, ITEMS)
            for j, bg in enumerate(ghi):
                do += [f"{s['id']} lượt {j + 1}: {d}" for d in R.cham_luot(bg, ghi[:j])]
        self.assertEqual(do, [], f"{len(do)} lượt đỏ trong nhóm CHỐT — đây là CHẶN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
