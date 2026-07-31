# -*- coding: utf-8 -*-
"""Phép kiểm sức khỏe sau deploy phải hỏi những trường mà dịch vụ THẬT SỰ trả.

Vì sao tệp này tồn tại
----------------------
`deploy/scripts/health-check.sh` là **đầu thứ hai** của hợp đồng HTTP, và nó viết bằng Python nội
tuyến trong Bash — nên không compiler, không linter, không test nào chạm tới nó. Kết quả đã xảy ra
thật ngày 2026-07-31: dịch vụ mới lên staging, `/ready` trả **đúng mọi thứ mong đợi**, và deploy vẫn
đỏ vì phép kiểm hỏi `pipeline_profile` và `model_policy` — trường của hệ thống cũ:

    retriever=embedding · retriever_vectors_from_cache=True · generation_enabled=False
    menu_items=91 · knowledge_chunks=449         <- dịch vụ khỏe
    AssertionError                               <- phép kiểm hỏi trường không còn tồn tại

Đây là lần thứ **tám** trong dự án này một bất biến "hai đầu phải khớp" chỉ được sửa ở một đầu, và
lần thứ tư đầu còn lại nằm ở ngôn ngữ khác (trước đó: TypeScript đọc `requirements-rag.txt`, C# đọc
`verify_pipeline_selection.py`, JSON schema `maxItems`). Mỗi lần tôi sửa xong lại nói "lần sau nhớ
kiểm cả hai đầu", và lần sau vẫn quên. **Nhắc mình không phải là cơ chế.** Test là cơ chế.

Cách kiểm: đối chiếu, không so chuỗi
------------------------------------
Test này KHÔNG kiểm "script có chứa chữ `retriever`". Nó bóc mọi khóa mà script hỏi, rồi so với khóa
mà dịch vụ thật trả về:

    script hỏi payload.get("X")     ->  X phải có trong phản hồi /ready thật
    script hỏi decision.get("Y")    ->  Y phải có trong decision thật
    script hỏi action.get("Z")      ->  Z phải có trong một thẻ giỏ thật

Nhờ vậy nó bắt được cả hướng ngược: xóa một trường khỏi `/ready` mà quên sửa phép kiểm deploy cũng
đỏ ngay ở CI, chứ không đợi tới lúc deploy.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "deploy" / "scripts" / "health-check.sh"

TOKEN = "token-thu-nghiem-health-check"

try:  # cùng lý do bỏ qua như test_service: phần dữ liệu của dự án chỉ dùng thư viện chuẩn
    from fastapi.testclient import TestClient

    import service as service_module

    HAVE_DEPS = True
    IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
    HAVE_DEPS = False
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def _khoi_python(script: str) -> list[str]:
    """Mọi khối `python3 - ... <<'PY' ... PY` trong script."""
    return re.findall(r"<<'PY'\n(.*?)\nPY\n", script, re.DOTALL)


def _khoa(khoi: str, bien: str) -> set[str]:
    """Mọi khóa mà khối này hỏi qua `<bien>.get("...")`."""
    return set(re.findall(rf'\b{re.escape(bien)}\.get\("([^"]+)"\)', khoi))


class ScriptPhaiDocDuoc(unittest.TestCase):
    def test_script_ton_tai(self):
        self.assertTrue(SCRIPT.exists(), f"thiếu {SCRIPT}")

    def test_boc_duoc_cac_khoi_python(self):
        """Nếu bộ bóc không tìm thấy khối nào thì mọi test dưới sẽ xanh vì RỖNG.

        Đây là lớp lỗi đã xảy ra một lần thật ở `test_packaging.py`: bộ phân tích đọc sai định dạng
        nên tập khóa rỗng, và test xanh trong khi không kiểm gì. Nên bộ bóc phải tự có test.
        """
        khoi = _khoi_python(SCRIPT.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(khoi), 4, f"chỉ bóc được {len(khoi)} khối python — bộ bóc sai?")

    def test_KHONG_con_truong_cua_he_thong_cu(self):
        """Danh sách này là đúng những trường đã làm deploy đỏ ngày 2026-07-31."""
        script = SCRIPT.read_text(encoding="utf-8")
        # Cắt phần chú thích đầu tệp: nó KỂ LẠI những tên này, và kể lại là đúng việc của nó.
        than = script.split("set -euo pipefail", 1)[-1]
        for ten in (
            "pipeline_profile",
            "model_policy",
            "primary_model",
            "provider_status",
            "model_attempts",
            "verifier_result",
            "resolved_menu_item_ids",
            "fallback_model",
            "AI_PIPELINE_PROFILE",
        ):
            with self.subTest(ten):
                self.assertNotIn(
                    ten,
                    than,
                    f"phép kiểm deploy còn hỏi `{ten}` — trường của hệ thống AI đã bị thay",
                )

    def test_khong_viet_tay_ky_vong_ve_bo_truy_hoi(self):
        """`retriever` mong đợi phải suy từ mã, không gõ vào script.

        Gõ `"embedding"` vào đây là tạo ra một con số viết tay thứ tám để trôi. Nó phải đến từ
        `verify_deploy_config.bo_truy_hoi_se_deploy()` — cùng nguồn mà cổng deploy dùng.
        """
        than = SCRIPT.read_text(encoding="utf-8").split("set -euo pipefail", 1)[-1]
        self.assertIn("verify_deploy_config", than)
        self.assertIn("bo_truy_hoi_se_deploy", than)
        self.assertIn("duong_sinh_se_bat", than)

        # Cấm GÁN thẳng, không cấm nhắc tên. Script vẫn phải so `expected_retriever == "embedding"`
        # để biết có kiểm đệm vector hay không — đó là dùng giá trị đã suy ra, không phải viết tay.
        # Bản đầu của test này cấm mọi lần xuất hiện chuỗi `"embedding"` nên nó đỏ với đúng cách
        # dùng hợp lệ: một phép kiểm quá rộng bắt cả thứ nó không có ý bắt.
        gan_tay = re.findall(
            r'^\s*expected_(?:retriever|generation)=(?![\"\']?\$)(.*)$', than, re.MULTILINE
        )
        self.assertFalse(
            gan_tay,
            f"kỳ vọng bị gán thẳng vào script: {gan_tay} — phải suy từ verify_deploy_config",
        )

    def test_ham_script_goi_that_su_ton_tai(self):
        """Script gọi hai hàm bằng tên chuỗi, nên đổi tên hàm là làm deploy đỏ mà không ai biết."""
        sys.path.insert(0, str(REPO_ROOT / "ai" / "evaluation"))
        import verify_deploy_config as gate

        self.assertTrue(callable(gate.bo_truy_hoi_se_deploy))
        self.assertTrue(callable(gate.duong_sinh_se_bat))
        self.assertIn(gate.bo_truy_hoi_se_deploy(), ("embedding", "bm25"))
        self.assertIsInstance(gate.duong_sinh_se_bat(), bool)


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class KhoaScriptHoiPhaiCoThat(unittest.TestCase):
    """Đối chiếu từng khóa script hỏi với phản hồi THẬT của dịch vụ."""

    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)
        self.khoi = _khoi_python(SCRIPT.read_text(encoding="utf-8"))

    def _khoi_chua(self, dau_hieu: str) -> str:
        ung_vien = [k for k in self.khoi if dau_hieu in k]
        self.assertEqual(
            len(ung_vien),
            1,
            f"cần đúng một khối python chứa `{dau_hieu}`, tìm được {len(ung_vien)}",
        )
        return ung_vien[0]

    def test_moi_khoa_ready_script_hoi_deu_co_that(self):
        that = set(self.client.get("/ready").json())
        hoi = _khoa(self._khoi_chua("expected_retriever"), "payload")
        thieu = hoi - that
        self.assertFalse(
            thieu,
            f"phép kiểm deploy hỏi {sorted(thieu)} nhưng /ready không trả — deploy sẽ đỏ trong "
            f"khi dịch vụ khỏe. /ready trả: {sorted(that)}",
        )

    def test_moi_khoa_chat_script_hoi_deu_co_that(self):
        # `use_model: True` chứ không phải False, và đó là điểm chính: khi tắt mô hình thì
        # `decision.model` là `null`, nên bộ khóa rỗng và phép so `decision.model.*` xanh vì KHÔNG
        # KIỂM GÌ. Dịch vụ chạy thật luôn có nhánh mô hình, nên phải so với hình dạng đó.
        # Không cần khóa API: câu này từ vựng tất định hiểu đủ nên không có lần gọi mạng nào.
        body = self.client.post(
            "/v1/chat",
            json={"question": "Nhà hàng mình có những món phở gì nhỉ?", "use_model": True},
            headers={"x-internal-token": TOKEN},
        ).json()
        self.assertIsInstance(
            body["decision"]["model"],
            dict,
            "decision.model là null nên phép so khóa dưới sẽ xanh vì rỗng",
        )
        khoi = self._khoi_chua("suggested_cart_actions")

        thieu = _khoa(khoi, "payload") - set(body)
        self.assertFalse(thieu, f"script hỏi {sorted(thieu)} ngoài phản hồi /v1/chat: {sorted(body)}")

        thieu_qd = _khoa(khoi, "decision") - set(body["decision"])
        self.assertFalse(
            thieu_qd,
            f"script hỏi decision.{sorted(thieu_qd)} nhưng decision trả: {sorted(body['decision'])}",
        )

        thieu_mh = _khoa(khoi, "model") - set(body["decision"]["model"] or {})
        self.assertFalse(thieu_mh, f"script hỏi decision.model.{sorted(thieu_mh)} — không có")

        cart = body["suggested_cart_actions"]
        self.assertTrue(cart, "câu hỏi phở phải sinh thẻ giỏ, nếu không phép so dưới là rỗng")
        thieu_the = _khoa(khoi, "action") - set(cart[0])
        self.assertFalse(thieu_the, f"script hỏi action.{sorted(thieu_the)} — thẻ giỏ không có")

    def test_moi_khoa_backend_stream_script_hoi_deu_dung_ten_camelCase(self):
        """Khối cuối đọc phản hồi của BACKEND (C#), nên tên trường là camelCase.

        Không gọi được backend từ đây, nên điều kiểm được là: script không lẫn tên snake_case của
        dịch vụ AI vào khối đọc backend — đúng lớp lỗi đã trộn hai hợp đồng vào một chỗ.
        """
        khoi = self._khoi_chua("guardrailFlags")
        for khoa in _khoa(khoi, "final_payload"):
            with self.subTest(khoa):
                self.assertNotIn("_", khoa, f"`{khoa}` trông như tên của dịch vụ AI, không phải backend")

    def test_cum_bi_cam_phai_thuc_su_xuat_hien_trong_cau_tu_choi_that(self):
        """Script cấm vài cụm xuất hiện trong câu trả lời. Những cụm đó phải là cụm hệ thống THẬT nói.

        Cấm một cụm mà hệ thống không bao giờ nói là một phép kiểm chết — nó xanh mãi mãi và không
        bảo vệ gì. Câu từ chối là chuỗi ghép tại chỗ, không phải hằng mô-đun, nên cách duy nhất biết
        nó nói gì là **hỏi dịch vụ** rồi so.

        Đúng lỗi này vừa xảy ra khi tôi viết lại script: tôi cấm "tôi chưa có dữ liệu về câu hỏi
        này" trong khi hệ thống nói "Mình chưa có dữ liệu về việc này ạ."
        """
        khoi = self._khoi_chua("suggested_cart_actions")
        khop = re.search(r"for forbidden_phrase in \(\n(.*?)\n\):", khoi, re.DOTALL)
        self.assertIsNotNone(khop, "không tìm được danh sách cụm bị cấm trong script")
        cum = re.findall(r'"([^"]+)"', khop.group(1))
        self.assertTrue(cum, "danh sách cụm bị cấm rỗng")

        tu_choi = self.client.post(
            "/v1/chat",
            json={"question": "Đầu bếp tên gì?", "use_model": False},
            headers={"x-internal-token": TOKEN},
        ).json()
        self.assertEqual(tu_choi["decision"]["kind"], "no_data", tu_choi["content"])
        noi_dung = tu_choi["content"].casefold()

        self.assertTrue(
            any(c in noi_dung for c in cum),
            f"không cụm nào trong {cum} xuất hiện ở câu từ chối thật "
            f"({tu_choi['content']!r}) — phép kiểm deploy đang canh một câu không tồn tại",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
