# -*- coding: utf-8 -*-
"""Hợp đồng schema phải mô tả ĐÚNG thứ dịch vụ thật trả ra.

Vì sao tệp này tồn tại
----------------------
Phép kiểm hợp đồng ở phía backend (`AiContractBoundaryTests.cs`) chỉ đòi tệp schema **chứa ba
chuỗi**: `"ChatRequest"`, `"ChatResponse"`, `suggested_cart_actions`. Một tệp chứa ba chuỗi đó mà
mô tả sai hoàn toàn cũng qua được.

Và **schema không khớp thực tế thì tệ hơn không có schema**: người đọc nó tưởng mình biết hợp
đồng, rồi viết mã theo một hợp đồng không tồn tại. Bản cũ có đúng dạng vấn đề đó — hợp đồng 24
trường trong khi 4 trường luôn rỗng.

Nên tệp này lấy **phản hồi THẬT** từ dịch vụ rồi kiểm nó theo schema. Nếu ai sửa `service.py` mà
quên sửa schema (hoặc ngược lại), test đỏ.

`additionalProperties: false` trong schema là thứ làm việc này có nghĩa: nó biến "thêm một trường
mà quên khai" thành lỗi, chứ không phải im lặng cho qua.

    python -m unittest test_contract      # trong ai/app
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOKEN = "token-thu-nghiem-contract"

# Token của tệp test này. Đặt trong `setUp` của từng lớp, KHÔNG đặt ở cấp module.
#
# Vì sao: biến môi trường là trạng thái toàn cục của cả tiến trình. Đặt lúc nạp module thì module
# nào nạp SAU sẽ thắng, và module kia gửi token cũ nên nhận 401. Đã xảy ra thật: `test_service`
# và `test_contract` dùng hai token khác nhau, chạy riêng thì cả hai xanh còn chạy chung thì 12
# lỗi. Mỗi test phải tự dựng điều kiện của mình.

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "contracts" / "ai-chat-v1.schema.json"

try:
    import jsonschema
    from fastapi.testclient import TestClient

    import service as service_module

    HAVE_DEPS, IMPORT_ERROR = True, ""
except Exception as exc:  # noqa: BLE001
    HAVE_DEPS, IMPORT_ERROR = False, f"{type(exc).__name__}: {exc}"

REQUIRED = os.environ.get("AI_REQUIRE_SERVICE_TESTS") == "1"


class SchemaTonTaiVaHopLe(unittest.TestCase):
    """Chạy được không cần fastapi — chỉ đọc tệp."""

    def test_tep_schema_ton_tai(self):
        self.assertTrue(SCHEMA_PATH.exists(), f"thiếu {SCHEMA_PATH.name}")

    def test_la_json_hop_le(self):
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_co_du_ba_chuoi_phep_kiem_backend_doi(self):
        """`AiContractBoundaryTests.cs` bỏ qua chính nó khi tệp schema không tồn tại.

        Đó là lựa chọn đúng lúc dựng lại (test đỏ suốt thì người ta học cách bỏ qua nó), nhưng nó
        nghĩa là phép kiểm phía backend **im lặng vô hiệu** nếu tệp bị xóa. Test này ở phía Python
        làm việc xóa tệp thành lỗi thấy được.
        """
        raw = SCHEMA_PATH.read_text(encoding="utf-8")
        for chuoi in ('"ChatRequest"', '"ChatResponse"', "suggested_cart_actions"):
            self.assertIn(chuoi, raw, f"thiếu {chuoi!r} — phép kiểm backend sẽ đỏ")

    def test_requires_customer_confirmation_la_CONST_khong_phai_boolean(self):
        """Ranh giới 'AI không tự đặt món' phải là hằng số trong hợp đồng, không phải một trường
        có thể mang giá trị nào cũng được."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        prop = schema["$defs"]["SuggestedCartAction"]["properties"][
            "requires_customer_confirmation"
        ]
        self.assertEqual(prop.get("const"), True, "phải là `const: true`, không phải `type: boolean`")

    def test_KHONG_khai_truong_thuoc_quyen_backend(self):
        """Kiểm THUỘC TÍNH ĐÃ KHAI, không kiểm chuỗi trong văn bản.

        Bản đầu của test này quét chuỗi trên toàn tệp và đỏ ngay — vì hai tên trường đó xuất hiện
        trong phần `description`, đúng chỗ tôi giải thích *vì sao cố ý không có chúng*. Test bắt
        đúng chuỗi nhưng sai chỗ: nó biến việc GIẢI THÍCH một quyết định thành vi phạm quyết định
        đó.

        Đây lại là lớp `criterion_too_strict`, và dấu hiệu vẫn như cũ: thông báo lỗi dài mà thứ nó
        chỉ vào lại là văn bản giải thích, không phải mã.
        """
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        khai = set(schema["$defs"]["SessionUpdates"]["properties"])
        for ten in ("accepted_menu_item_ids", "added_to_cart_menu_item_ids"):
            self.assertNotIn(
                ten, khai,
                f"{ten!r} thuộc quyền backend — khai nó trong hợp đồng AI là nói sai ranh giới",
            )
        # Và `additionalProperties: false` là thứ làm việc "không khai" có hiệu lực thật.
        self.assertIs(schema["$defs"]["SessionUpdates"]["additionalProperties"], False)


class ThuVienPhaiCoKhiCIYEUCAU(unittest.TestCase):
    def test_ci_phai_co_jsonschema_va_fastapi(self):
        if not REQUIRED:
            self.skipTest("chỉ ép khi AI_REQUIRE_SERVICE_TESTS=1")
        self.assertTrue(HAVE_DEPS, f"CI yêu cầu test hợp đồng phải CHẠY: {IMPORT_ERROR}")


@unittest.skipUnless(HAVE_DEPS, f"thiếu jsonschema/fastapi ({IMPORT_ERROR})")
class PhanHoiTHATPhaiKhopSchema(unittest.TestCase):
    """Đây là phần đáng giá nhất của tệp: đối chiếu schema với thực tế, không với ý định."""

    CAU = (
        "Mình dị ứng hải sản, gợi ý món ăn giúp mình",
        "Cho mình món chay dưới 100 nghìn",
        "Phở bò tái nạm bao nhiêu tiền?",
        "Nhà hàng mấy giờ mở cửa?",
        "Hôm nay thời tiết thế nào?",
        "Gợi ý món đi",
        "Món này bao nhiêu calo?",
        "So sánh Phở bò tái nạm và Bún bò Huế",
    )

    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.response_schema = {**self.schema, "$ref": "#/$defs/ChatResponse"}
        self.response_schema.pop("oneOf", None)

    def _check(self, payload: dict) -> None:
        jsonschema.validate(payload, self.response_schema)

    def test_moi_dang_cau_hoi_cho_phan_hoi_khop_schema(self):
        for cau in self.CAU:
            with self.subTest(cau):
                body = self.client.post(
                    "/v1/chat", json={"question": cau, "use_model": False},
                    headers={"x-internal-token": TOKEN},
                ).json()
                self._check(body)

    def test_phan_hoi_LOI_NOI_BO_cung_khop_schema(self):
        """Đường lỗi cũng phải khớp hợp đồng. Nếu không thì backend gặp hình dạng lạ đúng lúc
        hệ thống đang có sự cố — thời điểm tệ nhất."""
        goc = service_module.respond

        def no(*_a, **_k):
            raise RuntimeError("lỗi giả")

        service_module.respond = no
        try:
            body = self.client.post("/v1/chat", json={"question": "x", "use_model": False},
                                    headers={"x-internal-token": TOKEN}).json()
        finally:
            service_module.respond = goc
        self._check(body)
        self.assertFalse(body["ok"])

    def test_phan_hoi_nhieu_luot_co_bo_nho_cung_khop(self):
        state = None
        for cau in ("Mình dị ứng hải sản", "Món nào rẻ hơn?", "Cho mình món không cay"):
            body = self.client.post(
                "/v1/chat",
                json={"question": cau, "session_state": state, "use_model": False},
                headers={"x-internal-token": TOKEN},
            ).json()
            with self.subTest(cau):
                self._check(body)
            state = body["session_updates"]["session_state"]

    def test_them_truong_khong_khai_thi_schema_BAT_duoc(self):
        """Chiều ngược: nếu schema cho qua mọi thứ thì các test trên vô nghĩa.

        `additionalProperties: false` là thứ làm việc "thêm trường mà quên khai" thành lỗi.
        """
        body = self.client.post("/v1/chat", json={"question": "Cho mình món chay",
                                                  "use_model": False},
                                headers={"x-internal-token": TOKEN}).json()
        self._check(body)                       # bản gốc phải khớp
        body["truong_la_khong_khai_trong_schema"] = 1
        with self.assertRaises(jsonschema.ValidationError):
            self._check(body)

    def test_BA_cho_giu_so_mon_phai_KHOP_nhau(self):
        """`LIST_SIZE` (số món NÊU) == `MAX_CART_ACTIONS` (số thẻ) == `maxItems` (hợp đồng).

        Ba chỗ, và chúng ĐÃ lệch: `LIST_SIZE = 6` còn hai chỗ kia là 3. Hậu quả đo được khi hỏi stack
        thật — câu trả lời nêu SÁU món, thẻ giỏ có BA, nên khách đọc sáu lựa chọn và bấm chọn được ba;
        ba món còn lại phải gõ tay.

        Golden KHÔNG bắt được: bất biến thẻ giỏ đòi *thẻ ⊆ món được nêu*, không đòi chiều ngược lại.
        Một bất biến một chiều chỉ canh một nửa — nay golden có thêm bất biến số 8 cho chiều còn lại.

        `cart.MAX_CART_ACTIONS` nay LẤY TỪ `answer.LIST_SIZE` nên hai chỗ đó không lệch được nữa. Chỗ
        thứ ba là JSON, không import được — nên nó cần đúng test này. Đây là dạng "hai đầu phải khớp"
        thứ năm trong dự án, và lần này đầu thứ hai là một tệp không phải mã.
        """
        from answer import LIST_SIZE
        from cart import MAX_CART_ACTIONS

        trong_hop_dong = (
            self.schema["$defs"]["ChatResponse"]["properties"]["suggested_cart_actions"]["maxItems"]
        )
        self.assertEqual(
            (LIST_SIZE, MAX_CART_ACTIONS, trong_hop_dong),
            (LIST_SIZE, LIST_SIZE, LIST_SIZE),
            f"ba chỗ giữ số món đã lệch: LIST_SIZE={LIST_SIZE}, "
            f"MAX_CART_ACTIONS={MAX_CART_ACTIONS}, maxItems={trong_hop_dong}",
        )

    def test_yeu_cau_gui_len_cung_khop_schema_ChatRequest(self):
        request_schema = {**self.schema, "$ref": "#/$defs/ChatRequest"}
        request_schema.pop("oneOf", None)
        for payload in (
            {"question": "Cho mình món chay"},
            {"question": "Món nào rẻ hơn?", "session_state": None, "use_model": False},
            {"question": "x", "session_state": {"avoid_tags": ["allergen:seafood"]}},
        ):
            with self.subTest(str(payload)[:40]):
                jsonschema.validate(payload, request_schema)


if __name__ == "__main__":
    unittest.main(verbosity=2)
