# -*- coding: utf-8 -*-
"""Test hợp đồng HTTP của dịch vụ AI.

Hai nhóm bất biến quan trọng nhất:

1. **Lớp vỏ không được đổi nội dung.** Mọi con số của dự án (122/122 tất định, 0 lỗi an toàn) đo
   trên `understand → session → answer`. Nếu `service.py` đổi câu trả lời thì những con số đó
   không còn nói về thứ khách nhận được. Có test đòi 5 câu qua HTTP cho **cùng `content` và cùng
   danh sách món** với khi gọi `respond()` trực tiếp.

2. **Lỗi nội bộ KHÔNG được thành 500.** Khách đang ngồi ở bàn: 500 là màn hình lỗi, còn câu
   chuyển nhân viên là vẫn được phục vụ. Dự án đã mắc lỗi này theo hướng ngược một lần —
   `urllib.request.Request(...)` nằm ngoài khối `try` nên thiếu cấu hình là **sập**, trong khi tài
   liệu khẳng định nó thoái hóa êm. Bài học: **khẳng định về hành vi khi lỗi phải có test cho đúng
   đường lỗi đó.** Nên ở đây có test TIÊM LỖI vào `respond()`.

Về việc bỏ qua test
-------------------
Tệp này cần `fastapi` và `httpx`, còn phần dữ liệu/thước đo của dự án chỉ dùng thư viện chuẩn. Nên
test tự bỏ qua khi thiếu thư viện, để `unittest discover -s ai/app` không vỡ với người chưa cài.

Nhưng **bỏ qua âm thầm trong CI là test dối**. Nên có `AI_REQUIRE_SERVICE_TESTS=1`: khi biến đó
được đặt (CI đặt), thiếu thư viện là **LỖI** chứ không phải bỏ qua.

    python -m unittest test_service      # trong ai/app
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TOKEN = "token-thu-nghiem"

# Token của tệp test này. Đặt trong `setUp` của từng lớp, KHÔNG đặt ở cấp module.
#
# Vì sao: biến môi trường là trạng thái toàn cục của cả tiến trình. Đặt lúc nạp module thì module
# nào nạp SAU sẽ thắng, và module kia gửi token cũ nên nhận 401. Đã xảy ra thật: `test_service`
# và `test_contract` dùng hai token khác nhau, chạy riêng thì cả hai xanh còn chạy chung thì 12
# lỗi. Mỗi test phải tự dựng điều kiện của mình.

try:
    from fastapi.testclient import TestClient

    import service as service_module

    HAVE_DEPS, IMPORT_ERROR = True, ""
except Exception as exc:  # noqa: BLE001
    HAVE_DEPS, IMPORT_ERROR = False, f"{type(exc).__name__}: {exc}"

REQUIRED = os.environ.get("AI_REQUIRE_SERVICE_TESTS") == "1"


class ThuVienPhaiCoKhiCIYEUCAU(unittest.TestCase):
    """Chặn việc test dịch vụ bị bỏ qua âm thầm trong CI."""

    def test_ci_phai_co_fastapi(self):
        if not REQUIRED:
            self.skipTest("chỉ ép khi AI_REQUIRE_SERVICE_TESTS=1 (CI đặt biến này)")
        self.assertTrue(
            HAVE_DEPS,
            f"CI yêu cầu test dịch vụ phải CHẠY nhưng thiếu thư viện: {IMPORT_ERROR}. "
            "Cài `fastapi` và `httpx` trong bước CI, đừng để test bị bỏ qua.",
        )


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class XacThucToken(unittest.TestCase):
    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    def test_thieu_token_thi_401(self):
        r = self.client.post("/v1/chat", json={"question": "Có món chay không?"})
        self.assertEqual(r.status_code, 401)

    def test_token_sai_thi_401(self):
        r = self.client.post("/v1/chat", json={"question": "Có món chay không?"},
                             headers={"x-internal-token": "sai-be-bet"})
        self.assertEqual(r.status_code, 401)

    def test_token_dung_thi_200(self):
        r = self.client.post("/v1/chat", json={"question": "Có món chay không?", "use_model": False},
                             headers={"x-internal-token": TOKEN})
        self.assertEqual(r.status_code, 200)

    def test_token_trong_trong_moi_truong_thi_TU_CHOI_het(self):
        """Cấu hình thiếu mà mở cửa là cách một dịch vụ nội bộ thành công khai mà không ai biết."""
        cu = os.environ.get("AI_INTERNAL_TOKEN")
        os.environ["AI_INTERNAL_TOKEN"] = ""
        try:
            r = self.client.post("/v1/chat", json={"question": "x"},
                                 headers={"x-internal-token": ""})
            self.assertEqual(r.status_code, 503)
        finally:
            os.environ["AI_INTERNAL_TOKEN"] = cu or TOKEN

    def test_nhan_token_qua_Authorization_Bearer(self):
        """Backend .NET gửi token bằng `Authorization: Bearer`, không phải `X-Internal-Token`.

        Bản đầu chỉ đọc `X-Internal-Token` nên MỌI lượt chat từ backend nhận 401 và khách thấy
        "Xin lỗi, hệ thống hơi chậm". Không test nào bắt được vì mọi test đều tự gửi header của
        hợp đồng dịch vụ — tức chúng kiểm hợp đồng tôi TƯỞNG, không kiểm hợp đồng bên gọi DÙNG.
        """
        r = self.client.post(
            "/v1/chat", json={"message": "Có món chay không?", "use_model": False},
            headers={"authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(r.status_code, 200, "backend gửi Bearer — phải nhận được")
        self.assertTrue(r.json()["content"])

    def test_Authorization_Bearer_SAI_thi_van_401(self):
        r = self.client.post(
            "/v1/chat", json={"message": "x", "use_model": False},
            headers={"authorization": "Bearer sai-be-bet"},
        )
        self.assertEqual(r.status_code, 401)

    def test_nhan_truong_message_nhu_backend_gui(self):
        """Backend gửi `message`; hợp đồng dịch vụ dùng `question`. Phải nhận cả hai."""
        for khoa in ("message", "question"):
            with self.subTest(khoa):
                r = self.client.post(
                    "/v1/chat", json={khoa: "Cho mình món chay", "use_model": False},
                    headers={"x-internal-token": TOKEN},
                )
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.json()["content"])

    def test_bo_qua_truong_LA_cua_backend_thay_vi_tu_choi(self):
        """Backend gửi 24 trường. Từ chối trường lạ là bắt backend đổi để khớp dịch vụ mới —
        phá hợp đồng khách hàng, đúng thứ bản dựng lại cam kết không làm."""
        r = self.client.post(
            "/v1/chat",
            json={"message": "Cho mình món chay", "use_model": False,
                  "contract_version": "v2", "pipeline_profile": "llm_first_v1",
                  "table_code": "B01", "menu_items": [], "live_context": {},
                  "history": [], "facts": [], "catalog_version": "abc"},
            headers={"x-internal-token": TOKEN},
        )
        self.assertEqual(r.status_code, 200)

    def test_health_va_ready_KHONG_can_token(self):
        """Kiểm tra sức khỏe phải gọi được không cần token, nếu không orchestrator không dùng được."""
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/ready").status_code, 200)


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class HealthVaReadyKhacNhau(unittest.TestCase):
    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    def test_health_KHONG_kiem_du_lieu(self):
        """Trộn `/health` với `/ready` là lỗi thường gặp: một lỗi dữ liệu sẽ làm orchestrator khởi
        động lại container, mà khởi động lại không sửa được lỗi dữ liệu."""
        body = self.client.get("/health").json()
        self.assertTrue(body["ok"])
        self.assertNotIn("menu_items", body)

    def test_ready_bao_CON_SO_khong_chi_true_false(self):
        """Dịch vụ trả `ready: true` với 0 món là dịch vụ sẽ trả lời sai mọi câu.

        Đây là dạng khác của lỗi đã xảy ra thật: kho tri thức từng nằm ngoài phạm vi `COPY` của
        Dockerfile nên trong container mọi chủ đề chính sách trả "chưa có dữ liệu", im lặng.
        """
        body = self.client.get("/ready").json()
        self.assertTrue(body["ready"])
        self.assertEqual(body["menu_items"], 91)
        self.assertEqual(body["knowledge_docs"], 108)
        self.assertEqual(body["knowledge_chunks"], 449)
        self.assertEqual(body["verbatim_topics"], 24)

    def test_model_configured_PHAI_kiem_ca_khoa(self):
        """Thiếu `LLM_API_KEY` thì `model_configured` phải FALSE.

        Bản trước chỉ kiểm URL và tên mô hình. Container chạy với khóa rỗng (từ `deploy/.env`) vẫn
        báo `true`, và một phép đo đầu-cuối bị kết luận là "có mô hình thật" trong khi mọi lượt đi
        đường tất định — mô hình được gọi, thất bại ngay vì khóa rỗng, rồi hệ thống thoái hóa êm.

        Một trường trạng thái nói thiếu điều kiện tệ hơn không có trường: nó làm người đọc tin một
        điều đã được kiểm.
        """
        cu = {k: os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")}
        try:
            os.environ["LLM_BASE_URL"] = "http://x/v1"
            os.environ["LLM_MODEL"] = "m"
            os.environ["LLM_API_KEY"] = ""
            body = self.client.get("/ready").json()
            self.assertFalse(body["model_configured"], "thiếu khóa mà báo đã cấu hình")
            self.assertTrue(body["model_base_url_set"])
            self.assertFalse(body["model_key_set"])

            os.environ["LLM_API_KEY"] = "co-khoa"
            body = self.client.get("/ready").json()
            self.assertTrue(body["model_configured"])
            self.assertTrue(body["model_key_set"])
        finally:
            for k, v in cu.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_ready_bao_chua_san_sang_khi_thuc_don_rong(self):
        cu = service_module.MENU.items
        service_module.MENU.items = []
        try:
            body = self.client.get("/ready").json()
            self.assertFalse(body["ready"])
            self.assertEqual(body["menu_items"], 0)
        finally:
            service_module.MENU.items = cu


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class LopVoKhongDuocDoiNoiDung(unittest.TestCase):
    """Bất biến quan trọng nhất của tệp này. Nếu nó đỏ thì mọi con số của dự án mất ý nghĩa."""

    CAU = (
        "Mình dị ứng hải sản, gợi ý món ăn giúp mình",
        "Phở bò tái nạm bao nhiêu tiền?",
        "Nhà hàng mấy giờ mở cửa?",
        "Có món tráng miệng gì không?",
        "Món nào bán chạy nhất?",
    )

    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    def test_qua_http_cho_cung_ket_qua_voi_goi_truc_tiep(self):
        from answer import respond
        from understand import understand

        for cau in self.CAU:
            with self.subTest(cau):
                truc_tiep = respond(understand(cau, service_module.MENU.items),
                                    service_module.MENU.items)
                qua_http = self.client.post(
                    "/v1/chat", json={"question": cau, "use_model": False},
                    headers={"x-internal-token": TOKEN},
                ).json()
                self.assertEqual(qua_http["content"], truc_tiep.text)
                self.assertEqual(qua_http["decision"]["kind"], truc_tiep.kind)
                self.assertEqual(
                    qua_http["session_updates"]["referenced_menu_item_ids"], truc_tiep.items
                )


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class LoiNoiBoKHONGThanh500(unittest.TestCase):
    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    def test_respond_no_thi_van_200_kem_cau_chuyen_nhan_vien(self):
        """Tiêm lỗi vào đúng đường lỗi, thay vì tin lời khẳng định trong tài liệu."""
        goc = service_module.respond

        def no(*_a, **_k):
            raise RuntimeError("lỗi giả để kiểm đường lỗi")

        service_module.respond = no
        try:
            r = self.client.post("/v1/chat", json={"question": "Có món chay không?",
                                                   "use_model": False},
                                 headers={"x-internal-token": TOKEN})
        finally:
            service_module.respond = goc

        self.assertEqual(r.status_code, 200, "lỗi nội bộ KHÔNG được thành 500 cho khách")
        body = r.json()
        self.assertFalse(body["ok"])
        self.assertIn("nhân viên", body["content"])
        self.assertIn("internal_error", body["guardrail_flags"])
        self.assertTrue(body["suggest_staff_handoff"])
        self.assertIn("RuntimeError", body["decision"]["error"])

    def test_ly_do_that_KHONG_lot_vao_cau_khach_thay(self):
        """Lý do lỗi nằm trong `decision.error` cho người vận hành, không nằm trong câu khách."""
        goc = service_module.respond

        def no(*_a, **_k):
            raise RuntimeError("chi-tiet-noi-bo-khong-duoc-lo")

        service_module.respond = no
        try:
            body = self.client.post("/v1/chat", json={"question": "x", "use_model": False},
                                    headers={"x-internal-token": TOKEN}).json()
        finally:
            service_module.respond = goc
        self.assertNotIn("chi-tiet-noi-bo-khong-duoc-lo", body["content"])
        self.assertIn("chi-tiet-noi-bo-khong-duoc-lo", body["decision"]["error"])

    def test_cau_hoi_rong_thi_422_khong_phai_500(self):
        r = self.client.post("/v1/chat", json={"question": ""},
                             headers={"x-internal-token": TOKEN})
        self.assertEqual(r.status_code, 422)


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class BoNhoPhienQuaHTTP(unittest.TestCase):
    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    def _turn(self, question: str, state: dict | None):
        return self.client.post(
            "/v1/chat",
            json={"question": question, "session_state": state, "use_model": False},
            headers={"x-internal-token": TOKEN},
        ).json()

    def test_di_ung_giu_qua_nhieu_luot_HTTP(self):
        """Chốt an toàn, kiểm qua đúng đường khách đi — không phải gọi hàm trực tiếp."""
        items = {m["id"]: m for m in service_module.MENU.items}
        body = self._turn("Mình dị ứng hải sản", None)
        state = body["session_updates"]["session_state"]
        for cau in ("Món nào rẻ hơn?", "Cho mình món không cay", "Thêm món tráng miệng đi"):
            body = self._turn(cau, state)
            state = body["session_updates"]["session_state"]
            with self.subTest(cau):
                self.assertIn("allergen:seafood", state["avoid_tags"])
                bad = [
                    i for i in body["session_updates"]["referenced_menu_item_ids"]
                    if "allergen:seafood" in items[i]["tags"]
                ]
                self.assertEqual(bad, [], f"{cau!r}: nêu món mang nhãn hải sản")
                self.assertIn("allergen_filter_applied", body["guardrail_flags"])

    def test_bo_nho_hong_tu_mang_KHONG_lam_sap(self):
        for xau in ("khong-phai-dict", 42, {"avoid_tags": "sai kiểu"}, {"budget_max": -1}):
            with self.subTest(repr(xau)[:30]):
                r = self.client.post(
                    "/v1/chat",
                    json={"question": "Có món chay không?", "session_state": xau,
                          "use_model": False},
                    headers={"x-internal-token": TOKEN},
                )
                self.assertIn(r.status_code, (200, 422))

    def test_tom_tat_phien_co_trong_phan_hoi(self):
        body = self._turn("Mình dị ứng hải sản, cho món không cay dưới 200 nghìn", None)
        tom_tat = body["session_updates"]["rolling_summary"]
        self.assertIn("hải sản", tom_tat)
        self.assertIn("200.000đ", tom_tat)


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class HopDongTraVe(unittest.TestCase):
    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    def _body(self, question="Mình dị ứng hải sản, gợi ý món ăn giúp mình"):
        return self.client.post("/v1/chat", json={"question": question, "use_model": False},
                                headers={"x-internal-token": TOKEN}).json()

    def test_du_ten_truong_backend_doc(self):
        body = self._body()
        for key in ("ok", "provider_available", "content", "suggested_cart_actions",
                    "guardrail_flags", "suggest_staff_handoff", "session_updates", "decision"):
            self.assertIn(key, body)

    def test_KHONG_gui_truong_thuoc_quyen_backend(self):
        """AI đề xuất, khách xác nhận, backend quyết. Không gửi thì ranh giới rõ hơn là gửi rồi
        bị bỏ qua — `ApplyAiSessionUpdates` ghi rõ hai trường này thuộc backend."""
        updates = self._body()["session_updates"]
        self.assertNotIn("accepted_menu_item_ids", updates)
        self.assertNotIn("added_to_cart_menu_item_ids", updates)

    def test_the_gio_hang_qua_HTTP_ton_trong_du_bat_bien(self):
        """`cart.py` nay đã có. Kiểm qua đúng đường khách đi, không chỉ gọi hàm trực tiếp.

        Test này từng khẳng định thẻ giỏ RỖNG (khi `cart.py` chưa tồn tại). Đổi khẳng định thay
        vì xóa test, vì chỗ này là nơi duy nhất kiểm thẻ giỏ đi qua lớp HTTP đúng như backend gọi.
        """
        items = {m["id"]: m for m in service_module.MENU.items}
        cart = self._body()["suggested_cart_actions"]
        self.assertTrue(cart, "câu dị ứng vẫn phải nhận được gợi ý — fail-closed không nghĩa là "
                              "không mời gì")
        for action in cart:
            with self.subTest(action["name"]):
                # giá lấy từ thực đơn
                self.assertEqual(action["price"], items[action["menu_item_id"]]["price"])
                # luôn cần khách xác nhận
                self.assertTrue(action["requires_customer_confirmation"])
                # không món nào mang nhãn dị nguyên khách đã khai
                self.assertNotIn("allergen:seafood", items[action["menu_item_id"]]["tags"])
                # lý do nói "chưa/không ghi nhận", không nói "an toàn"
                self.assertNotIn("an toàn", action["reason"].lower())

    def test_nhanh_hoi_lai_qua_HTTP_KHONG_co_the_gio(self):
        """Gợi ý đặt món khi chưa hiểu câu hỏi là sai, và phải sai cả qua HTTP."""
        body = self._body("Gợi ý món đi")
        self.assertEqual(body["suggested_cart_actions"], [])

    def test_json_hoa_duoc_toan_bo(self):
        json.dumps(self._body(), ensure_ascii=False)


@unittest.skipUnless(HAVE_DEPS, f"thiếu fastapi/httpx ({IMPORT_ERROR})")
class StreamVaNapLai(unittest.TestCase):
    def setUp(self):
        os.environ["AI_INTERNAL_TOKEN"] = TOKEN
        self.client = TestClient(service_module.app, raise_server_exceptions=False)

    @staticmethod
    def _khung(text: str) -> list[tuple[str, dict]]:
        """Đọc SSE thành (tên khung, dữ liệu) — ĐÚNG cách backend đọc.

        Bản trước của test này chỉ quét dòng `data:` và bỏ qua dòng `event:`, nên nó xanh với một
        stream KHÔNG có dòng `event:` nào. Backend thì `continue` mọi dòng `data:` khi chưa thấy
        `event:`. Test tự nhất quán với chính nó, và cả stream bị hủy khi chạy thật.
        """
        khung: list[tuple[str, dict]] = []
        ten: str | None = None
        for dong in text.splitlines():
            if dong.startswith("event: "):
                ten = dong[len("event: "):].strip()
            elif dong.startswith("data: ") and ten:
                khung.append((ten, json.loads(dong[len("data: "):])))
        return khung

    def test_stream_phat_dung_KHUNG_ma_backend_doc(self):
        """Khung SSE phải có dòng `event:`, và tên khung do BÊN GỌI định.

        Đây là lỗi CHẶN PHÁT HÀNH đã xảy ra: dịch vụ phát `data: {"delta": ...}` không kèm dòng
        `event:`, backend bỏ qua toàn bộ, `finalPayload` null, và khách nhận "Xin lỗi, hệ thống hơi
        chậm." trên ĐƯỜNG CHÍNH — `ChatbotPage.tsx` gọi stream trước rồi mới lùi về gọi thường.

        Không test nào bắt được vì cả hai bên đều tự nhất quán: test này kiểm khung tự định, còn
        `ChatAiProviderV2ContractTests` kiểm bộ đọc của backend. Hai khung khác nhau, không tập nào
        nối hai bên. Golden test đầu-cuối là chỗ bắt được.
        """
        cau = "Có món chay nào không?"
        thuong = self.client.post("/v1/chat", json={"question": cau, "use_model": False},
                                  headers={"x-internal-token": TOKEN}).json()
        r = self.client.post("/v1/chat/stream", json={"question": cau, "use_model": False},
                             headers={"x-internal-token": TOKEN})
        self.assertEqual(r.status_code, 200)
        khung = self._khung(r.text)
        ten = [k for k, _ in khung]
        self.assertIn("token", ten, "thiếu khung `token`")
        self.assertIn("final", ten, "thiếu khung `final` — backend sẽ trả câu xin lỗi")
        self.assertEqual(ten[-1], "done", "khung cuối phải là `done`")
        cuoi = next(d for k, d in khung if k == "final")
        self.assertEqual(cuoi["content"], thuong["content"])
        # `final` phải mang ĐỦ payload, không chỉ nội dung: backend đọc thẻ giỏ và cờ từ khung này.
        for khoa in ("suggested_cart_actions", "guardrail_flags", "session_updates"):
            self.assertIn(khoa, cuoi, f"khung `final` thiếu {khoa}")

    def test_stream_cat_theo_TU_khong_theo_ky_tu(self):
        """Tiếng Việt có dấu tổ hợp; cắt giữa ký tự sẽ hiện ô vuông trên màn hình khách."""
        r = self.client.post("/v1/chat/stream",
                             json={"question": "Có món chay không?", "use_model": False},
                             headers={"x-internal-token": TOKEN})
        # Khóa là `text`, không phải `delta`: backend đọc `tokenData.TryGetProperty("text", ...)`.
        doan = [d.get("text") for k, d in self._khung(r.text) if k == "token"]
        doan = [d for d in doan if d]
        self.assertTrue(doan, "không có khung `token` nào mang `text`")
        for d in doan:
            self.assertTrue(d.endswith(" "), f"đoạn {d!r} không kết thúc bằng dấu cách")

    def test_nap_lai_thuc_don_bao_SO_MON(self):
        """Trả `{"ok": true}` thì một lần nạp thất bại nhìn giống một lần nạp thành công."""
        r = self.client.post("/v1/cache/invalidate", headers={"x-internal-token": TOKEN})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["menu_items"], 91)

    def test_nap_lai_can_token(self):
        self.assertEqual(self.client.post("/v1/cache/invalidate").status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)
