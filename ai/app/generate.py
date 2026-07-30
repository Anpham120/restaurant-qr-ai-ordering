# -*- coding: utf-8 -*-
"""Mô hình VIẾT câu trả lời — nhưng chỉ trên ngữ cảnh đã đưa vào, và có lớp xác minh.

Vì sao khâu này tồn tại, và nó đổi điều gì
------------------------------------------
Đề bài (`00-problem-statement.md` mục 3) phân ba loại câu và nói rõ mô hình sinh thuộc về đâu:

    loại A  tra cứu thực đơn   "KHÔNG được để mô hình sinh trả lời"
    loại B  tri thức nhà hàng  đoạn nguyên văn, mô hình không chạm chữ
    loại C  suy luận/diễn đạt  "Đây là nơi mô hình sinh có giá trị thật"

Cho tới trước tệp này, loại C cũng được trả bằng khuôn mẫu. Nên bảo đảm "không bịa món, không bịa
giá" là bảo đảm **cấu trúc**: mô hình không có đường ghi chữ cho khách, nên nó không thể bịa.

Tệp này đổi điều đó, và phải nói thẳng cái giá: bảo đảm chuyển từ **cấu trúc** sang **xác minh**.
Mạnh, đo được, nhưng không còn là bất khả. Ba việc giữ nó ở mức chấp nhận được:

1. **Mô hình KHÔNG chọn món.** Danh sách món do `answer.select()` lọc theo nhãn quyết định, và đo
   được là lọc theo nhãn thắng dứt khoát: 8/8 đúng so với RAG sai 6–7/8. Mô hình chỉ VIẾT về những
   món đã được chọn.
2. **Xác minh trước khi gửi.** Bốn phép kiểm ở `verify()` dưới đây. Vi phạm bất kỳ phép nào thì câu
   sinh bị BỎ và hệ thống dùng lại câu khuôn mẫu — không sửa, không thử lại.
3. **Thẻ giỏ vẫn tất định.** Nó dựng từ `reply.items`, không từ chữ mô hình viết. Nên dù một câu
   sinh lọt qua xác minh mà vẫn sai, khách không đặt được món không tồn tại.

Điều lớp này KHÔNG bắt được, nói ra chứ không giấu
--------------------------------------------------
Một tên món **hoàn toàn bịa** — không có trong thực đơn dưới bất kỳ dạng nào — thì phép so chuỗi
với thực đơn không phát hiện được. Ta bắt được: món thật nằm ngoài danh sách đã đưa, giá không có
trong thực đơn, và món mang nhãn khách cần tránh. Ta không bắt được "Bò sốt tiêu đen Hoàng Gia".

Giảm nhẹ chứ không xóa được: thẻ giỏ và `reply.items` vẫn tất định nên món bịa không đặt được, và
`golden_e2e` có phép kiểm số tiền trên câu trả lời thật. Đây là rủi ro còn lại của việc làm đúng đề
bài, và nó là lý do nhánh này chỉ chạy cho loại C.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from understand import Request

# Nhánh nào được phép sinh. CHỈ loại C — suy luận và diễn đạt.
#
# `filter` và `compare` là hai nhánh mà đề bài xếp vào loại C: chọn nhiều tiêu chí, hoặc cần diễn
# đạt. Mọi nhánh khác là tra cứu (loại A) hoặc tri thức nguyên văn (loại B), và đề bài cấm sinh ở
# loại A. `no_data`, `refuse`, `clarify` cũng không sinh: chưa hiểu câu hỏi thì không có gì để viết
# cho hay hơn, và một câu từ chối do mô hình viết là chỗ dễ rò rỉ nhất.
BRANCHES_ALLOWED = frozenset({"filter", "compare"})

# Số tiền trong câu trả lời. Dùng để kiểm mọi con số tiền đều là giá THẬT của món đã đưa vào.
MONEY_IN_TEXT = re.compile(r"\d[\d.]*(?=\s*đ)")

# Lời khai SỐ LƯỢNG món: "6 món lẩu", "có 3 món". Đo được ngay lần chạy thật đầu tiên: mô hình viết
# "Nhà hàng có 6 món lẩu" trong khi thực đơn có 7 — một con số bịa mà ba phép kiểm đầu không chạm
# tới, vì nó không phải tên món, không phải giá, và không phải nhãn.
#
# Cách chặn hẹp và chắc: mô hình KHÔNG được nêu số lượng. Nó không cần — nó đang viết về một danh
# sách đã đưa, và khách đọc thấy danh sách đó. Số lượng duy nhất đúng là số món trong danh sách,
# nên mọi con số khác là sai.
# Không dùng biên từ ở đây: tiếng Việt có dấu, và biên từ của `re` dựa trên `\w` nên nó cắt
# sai ở ký tự có dấu. Dùng lookahead cho khoảng trắng, dấu câu, hoặc hết chuỗi.
COUNT_IN_TEXT = re.compile(
    r"(\d+)\s*(?:món|loại|nồi|ly|phần)(?=[\s,.;:!?)]|$)", re.IGNORECASE
)

PROMPT = """Bạn viết câu trả lời cho khách trong nhà hàng Việt Nam, dựa TRÊN DỮ LIỆU ĐƯỢC ĐƯA.

QUY TẮC BẮT BUỘC:
1. Chỉ được nhắc những món có trong DANH SÁCH MÓN dưới đây. Không được nhắc món nào khác.
2. Giá phải viết đúng như trong danh sách. Không được làm tròn, không được đổi.
3. Không được nói món nào "an toàn" cho người dị ứng. Chỉ được nói thực đơn CÓ hoặc KHÔNG ghi nhận.
4. Không được thêm thông tin không có trong dữ liệu: không calo, không thời gian nấu, không nguồn
   gốc nguyên liệu, không khuyến mãi.
5. KHÔNG được nêu số lượng món ("có 6 món lẩu", "3 loại"). Bạn chỉ thấy một phần thực đơn, nên mọi
   con số đếm bạn viết ra đều có thể sai.
6. Viết 2–4 câu, tiếng Việt tự nhiên, giọng thân thiện nhưng không quảng cáo.
7. Nêu LÝ DO món phù hợp với điều khách nói, không chỉ liệt kê tên.

Trả về JSON đúng dạng:
{{"text": "câu trả lời", "used_item_ids": ["mã món đã nhắc"]}}

KHÁCH HỎI: {question}

ĐIỀU KHÁCH ĐÃ NÓI: {constraints}

DANH SÁCH MÓN (chỉ được nhắc những món này):
{items}
{knowledge}"""


@dataclass
class GenOutcome:
    """Kết quả một lần sinh. `text` là None nghĩa là dùng lại câu khuôn mẫu."""

    text: str | None = None
    used: list[str] = field(default_factory=list)
    # Vì sao bị bỏ, hoặc vì sao không gọi. Đi vào `decision` cho người vận hành, KHÔNG vào câu
    # khách đọc — cùng nguyên tắc với `decision.error` của dịch vụ.
    reason: str = ""
    violations: list[str] = field(default_factory=list)
    called: bool = False


def _mo_ta_rang_buoc(request: Request) -> str:
    """Điều khách đã nói, dạng chữ đọc được — để mô hình nêu LÝ DO đúng thứ khách nêu."""
    phan: list[str] = []
    if request.wants != "any":
        phan.append("muốn " + ("món ăn" if request.wants == "food" else "đồ uống"))
    if request.budget_max:
        moc = f"{request.budget_max:,}".replace(",", ".") + "đ"
        phan.append(f"ngân sách {'dưới' if request.budget_strict else 'tầm'} {moc}")
    if request.avoid_tags:
        phan.append("cần tránh: " + ", ".join(request.avoid_tags))
    if request.require_tags:
        phan.append("yêu cầu: " + ", ".join(request.require_tags))
    if request.prefer_tags:
        phan.append("thích: " + ", ".join(request.prefer_tags))
    return "; ".join(phan) or "chưa nêu ràng buộc cụ thể"


def _mo_ta_mon(items: list[dict]) -> str:
    dong: list[str] = []
    for i in items:
        gia = f"{i['price']:,}".replace(",", ".") + "đ"
        nhan = [t for t in i["tags"]
                if t.startswith(("spice:", "allergen:", "diet:", "region:", "method:"))]
        dong.append(f"- {i['id']} | {i['name']} | {gia} | {', '.join(sorted(nhan))}")
    return "\n".join(dong)


def verify(text: str, used: list[str], allowed: list[dict], all_items: list[dict],
           avoid_tags: list[str]) -> list[str]:
    """Bốn phép kiểm. Trả về danh sách vi phạm — rỗng nghĩa là câu sinh dùng được.

    Áp cho MỌI câu sinh, không khai từng ca: một phép kiểm chỉ chạy ở vài chỗ là một phép kiểm không
    bảo đảm gì.
    """
    loi: list[str] = []
    cho_phep = {i["id"] for i in allowed}
    ten_cho_phep = {i["name"] for i in allowed}
    gia_cho_phep = {i["price"] for i in allowed}

    # 1. Mã món mô hình khai đã dùng phải nằm trong danh sách đưa vào.
    la = sorted(set(used) - cho_phep)
    if la:
        loi.append(f"khai dùng món ngoài danh sách: {la}")

    # 2. KHÔNG được nhắc món thật nào NGOÀI danh sách. Đây là phép kiểm bắt được kiểu sai nguy hiểm
    #    nhất mà so chuỗi bắt được: mô hình lôi một món thật khác vào, đúng tên đúng giá, nhưng món
    #    đó không qua bộ lọc — nên nó có thể mang nhãn khách cần tránh.
    ngoai = sorted(i["name"] for i in all_items
                   if i["name"] in text and i["name"] not in ten_cho_phep)
    if ngoai:
        loi.append(f"nhắc món ngoài danh sách đã lọc: {ngoai}")

    # 3. Mọi số tiền phải là giá THẬT của một món đã đưa vào.
    for so in MONEY_IN_TEXT.findall(text):
        try:
            gia = int(so.replace(".", ""))
        except ValueError:
            continue
        if gia >= 1000 and gia not in gia_cho_phep:
            loi.append(f"số tiền {so}đ không phải giá của món nào trong danh sách")

    # 4. KHÔNG được nêu số lượng, trừ khi con số trùng số món trong danh sách.
    #
    # Đo được ở lần chạy thật đầu: "Nhà hàng có 6 món lẩu" — thực đơn có 7. Ba phép kiểm trên không
    # chạm tới vì nó không phải tên món, không phải giá, không phải nhãn. Đây là lớp bịa thứ tư, và
    # nó là lớp khó thấy nhất vì con số nghe rất tự nhiên.
    for so in COUNT_IN_TEXT.findall(text):
        try:
            n = int(so)
        except ValueError:
            continue
        if n != len(allowed):
            loi.append(
                f"nêu số lượng {n} món — mô hình chỉ thấy {len(allowed)} món nên mọi con số đếm "
                "khác đều có thể sai"
            )

    # 5. Nhãn khách cần tránh: không món nào được nhắc mang nhãn đó. CHỐT AN TOÀN.
    #    Đây là phép kiểm cuối cùng trước khi chữ tới khách, và nó lặp lại điều bộ lọc đã làm —
    #    lặp có chủ ý: bộ lọc chọn món, còn phép này kiểm chữ, và hai thứ đó lệch nhau được.
    for tag in avoid_tags:
        xau = sorted(i["name"] for i in all_items
                     if i["name"] in text and tag in i["tags"])
        if xau:
            loi.append(f"AN TOÀN: nhắc món mang `{tag}`: {xau}")
    return loi


def write_reply(request: Request, chosen: list[dict], all_items: list[dict], branch: str,
                env: dict[str, str], knowledge: str = "", *,
                call=None) -> GenOutcome:
    """Nhờ mô hình viết câu trả lời cho loại C. Trả `GenOutcome` với `text=None` nếu không dùng được.

    `call` cho phép test thay đường gọi mạng bằng một hàm giả — cùng cách `llm_understand` làm, và
    đó là lý do 26 test của nó chạy được không cần mạng.
    """
    if branch not in BRANCHES_ALLOWED:
        return GenOutcome(reason=f"nhánh `{branch}` không sinh (chỉ {sorted(BRANCHES_ALLOWED)})")
    if not chosen:
        return GenOutcome(reason="không có món nào để viết về")

    prompt = PROMPT.format(
        question=request.text,
        constraints=_mo_ta_rang_buoc(request),
        items=_mo_ta_mon(chosen),
        knowledge=f"\nTRI THỨC LIÊN QUAN:\n{knowledge}" if knowledge else "",
    )
    goi = call or _call_model
    parsed = goi(prompt, env)
    if parsed is None:
        return GenOutcome(reason="mô hình không trả về JSON dùng được", called=True)

    text = parsed.get("text")
    used = parsed.get("used_item_ids") or []
    if not isinstance(text, str) or not text.strip():
        return GenOutcome(reason="`text` rỗng hoặc sai kiểu", called=True)
    if not isinstance(used, list) or not all(isinstance(x, str) for x in used):
        return GenOutcome(reason="`used_item_ids` sai kiểu", called=True)

    loi = verify(text, used, chosen, all_items, list(request.avoid_tags))
    if loi:
        # BỎ câu sinh, không sửa và không thử lại. Sửa là đoán ý mô hình; thử lại là để một câu sai
        # có cơ hội thứ hai trong lúc khách đang chờ, và câu khuôn mẫu đã đúng sẵn.
        return GenOutcome(reason="không qua xác minh", violations=loi, called=True)
    return GenOutcome(text=" ".join(text.split()), used=used, called=True)


def _call_model(prompt: str, env: dict[str, str]) -> dict | None:
    """Gọi mô hình. Cùng đường mạng với `llm_understand.call_model`, khác prompt và khác cache.

    KHÔNG dùng cache: câu sinh phụ thuộc danh sách món, mà danh sách món phụ thuộc thực đơn và ràng
    buộc — nên khóa cache phải gồm cả hai, và một cache như vậy gần như không bao giờ trúng. Thà
    không cache còn hơn có một cache trúng 2% mà làm người đọc tin phép đo là tái lập được.
    """
    base_url = env.get("LLM_BASE_URL", "").strip()
    model = env.get("LLM_MODEL", "")
    if not base_url or not env.get("LLM_API_KEY", "").strip() or not model:
        return None
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 400,
    }).encode()
    try:
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {env['LLM_API_KEY'].strip()}",
            },
        )
        timeout = float(env.get("LLM_TIMEOUT_SECONDS", "30"))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
        content = payload["choices"][0]["message"]["content"]
    except (urllib.error.URLError, OSError, KeyError, ValueError, TypeError, TimeoutError):
        return None
    match = re.search(r"\{.*\}", content, re.S)
    if match is None:
        return None
    try:
        parsed = json.loads(match.group(0))
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None
