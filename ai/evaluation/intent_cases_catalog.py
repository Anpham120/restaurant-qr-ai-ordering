"""Canonical labeled cases for hybrid intent routing evaluation.

Regenerate JSONL:
    py -m evaluation.materialize_intent_cases
"""

from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = (
    "id",
    "message",
    "expected_wants_recommendations",
    "expected_party_size",
    "expected_is_solo_dining",
    "category",
    "tier",
    "language",
)

TIER_CORE = "core"
TIER_EDGE = "edge"
TIER_MULTI_TURN = "multi_turn"


def _case(
    id: str,
    message: str,
    *,
    wants: bool,
    party: int | None,
    solo: bool,
    category: str,
    tier: str = TIER_CORE,
    rationale: str = "",
    history: list[dict[str, str]] | None = None,
    expects_llm: bool | None = None,
    language: str = "vi",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": id,
        "message": message,
        "expected_wants_recommendations": wants,
        "expected_party_size": party,
        "expected_is_solo_dining": solo,
        "category": category,
        "tier": tier,
        "language": language,
        "rationale": rationale,
    }
    if history:
        row["history"] = history
    if expects_llm is not None:
        row["expects_llm"] = expects_llm
    return row


def build_intent_case_catalog() -> list[dict[str, Any]]:
    h = lambda *turns: [{"role": role, "content": text} for role, text in turns]

    cases: list[dict[str, Any]] = [
        # --- Solo dining (core bug regression) ---
        _case("solo_01", "di an solo toi nay", wants=True, party=1, solo=True, category="ambiguous_solo", tier=TIER_CORE, rationale="Tiếng lóng solo", expects_llm=True),
        _case("solo_02", "chi co minh toi thoi", wants=True, party=1, solo=True, category="ambiguous_solo", tier=TIER_CORE, rationale="Không có mot minh"),
        _case("solo_03", "hom nay minh di an mot minh", wants=True, party=1, solo=True, category="regex_solo", tier=TIER_CORE, rationale="Regex mot minh"),
        _case("solo_04", "toi di mot minh", wants=True, party=1, solo=True, category="regex_solo", tier=TIER_CORE),
        _case("solo_05", "an mot minh thi nen goi mon gi", wants=True, party=1, solo=True, category="regex_solo", tier=TIER_CORE),
        _case("solo_06", "tôi đi một mình tối nay", wants=True, party=1, solo=True, category="diacritics_vi", tier=TIER_CORE),
        _case("solo_07", "một mình ăn gì cho đỡ ngán", wants=True, party=1, solo=True, category="diacritics_vi", tier=TIER_CORE),
        _case("solo_08", "solo dining tonight", wants=True, party=1, solo=True, category="english", tier=TIER_EDGE, expects_llm=True),
        _case("solo_09", "di an mot minh thoi", wants=True, party=1, solo=True, category="typo_no_diacritics", tier=TIER_CORE),
        _case("solo_10", "minh an mot minh hom nay", wants=True, party=1, solo=True, category="typo_no_diacritics", tier=TIER_CORE),
        _case("solo_11", "toi an mot minh", wants=True, party=1, solo=True, category="regex_solo", tier=TIER_CORE),
        _case("solo_12", "di an mot minh", wants=True, party=1, solo=True, category="regex_solo", tier=TIER_CORE),
        _case("solo_13", "hom nay chi co minh toi", wants=True, party=1, solo=True, category="ambiguous_solo", tier=TIER_EDGE, expects_llm=True),
        _case("solo_14", "an 1 minh thi goi gi", wants=True, party=1, solo=True, category="ambiguous_solo", tier=TIER_EDGE, expects_llm=True),
        _case("solo_15", "just me tonight what to order", wants=True, party=1, solo=True, category="english", tier=TIER_EDGE, expects_llm=True),
        _case("solo_16", "minh di an 1 minh", wants=True, party=1, solo=True, category="ambiguous_solo", tier=TIER_EDGE, expects_llm=True),
        _case("solo_17", "eating alone recommend something", wants=True, party=1, solo=True, category="english", tier=TIER_EDGE, expects_llm=True),
        _case("solo_18", "tối nay em đi một mình", wants=True, party=1, solo=True, category="diacritics_vi", tier=TIER_CORE),
        _case("solo_19", "1 nguoi thoi goi mon gi", wants=True, party=1, solo=True, category="ambiguous_solo", tier=TIER_EDGE, expects_llm=True),
        _case("solo_20", "khach di mot minh nen goi gi", wants=True, party=1, solo=True, category="regex_solo", tier=TIER_CORE),
        # --- Restaurant info (must NOT recommend) ---
        _case("info_01", "wifi mat khau gi", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_02", "dia chi nha hang o dau", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_03", "gio mo cua may gio", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_04", "co cho gui xe khong", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_05", "hotline la so may", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_06", "thanh toan qr duoc khong", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_07", "phong vip co khong", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_08", "nha hang mo cua den may gio", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_09", "wifi password please", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("info_10", "địa chỉ quán ở đâu vậy", wants=False, party=None, solo=False, category="diacritics_vi", tier=TIER_CORE, expects_llm=False),
        _case("info_11", "co tra bang the khong", wants=False, party=None, solo=False, category="clear_info", tier=TIER_EDGE, expects_llm=False),
        _case("info_12", "suc chua phong bao nhieu nguoi", wants=False, party=None, solo=False, category="clear_info", tier=TIER_EDGE, expects_llm=False),
        _case("info_13", "nha ve sinh o dau", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_14", "co cho ngoi ngoai troi khong", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_15", "where is the restaurant", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("info_16", "do xe o dau vay", wants=False, party=None, solo=False, category="typo_no_diacritics", tier=TIER_CORE, expects_llm=False),
        _case("info_17", "lien he quan nhu the nao", wants=False, party=None, solo=False, category="clear_info", tier=TIER_CORE, expects_llm=False),
        _case("info_18", "co phong kin rieng khong", wants=False, party=None, solo=False, category="clear_info", tier=TIER_EDGE, expects_llm=False),
        _case("info_19", "opening hours today", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("info_20", "mat khau wifi la gi a", wants=False, party=None, solo=False, category="diacritics_vi", tier=TIER_CORE, expects_llm=False),
        # --- Party size ---
        _case("party_01", "8 nguoi an gi", wants=True, party=8, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_02", "4 nguoi goi mon gi", wants=True, party=4, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_03", "2 nguoi an gi", wants=True, party=2, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_04", "6 nguoi dat ban", wants=True, party=6, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_05", "10 nguoi an gi", wants=True, party=10, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_06", "3 nguoi nen goi mon gi", wants=True, party=3, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_07", "bon nguoi an gi", wants=True, party=4, solo=False, category="word_party", tier=TIER_EDGE, rationale="Chữ số bằng chữ"),
        _case("party_08", "ca nha 7 nguoi an gi", wants=True, party=7, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_09", "What should I eat for 4 people", wants=True, party=4, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("party_10", "5 nguoi an chung goi y", wants=True, party=5, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_11", "12 nguoi dat tiec", wants=True, party=12, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_12", "party of 6 recommend dishes", wants=True, party=6, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("party_13", "9 khach an gi", wants=True, party=9, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_14", "4 pax goi y mon", wants=True, party=4, solo=False, category="clear_party", tier=TIER_EDGE, expects_llm=False),
        _case("party_15", "cho 8 nguoi goi mon gi", wants=True, party=8, solo=False, category="clear_party", tier=TIER_CORE, expects_llm=False),
        _case("party_16", "nam nguoi an chung", wants=True, party=5, solo=False, category="word_party", tier=TIER_EDGE),
        _case("party_17", "sau nguoi goi y", wants=True, party=6, solo=False, category="word_party", tier=TIER_EDGE),
        _case("party_18", "bay nguoi an gi hom nay", wants=True, party=7, solo=False, category="word_party", tier=TIER_EDGE),
        # --- Recommendations ---
        _case("rec_01", "goi y mon chay", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_02", "mon cay vua thoi", wants=True, party=None, solo=False, category="ambiguous_dietary", tier=TIER_EDGE, expects_llm=True),
        _case("rec_03", "khong an hai san goi y gi", wants=True, party=None, solo=False, category="allergy_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_04", "an gi ngon hom nay", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_05", "de xuat mon pho", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_06", "tu van mon an sang", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_07", "mon keto co gi", wants=True, party=None, solo=False, category="ambiguous_dietary", tier=TIER_EDGE, expects_llm=True),
        _case("rec_08", "it calo nen an gi", wants=True, party=None, solo=False, category="dietary", tier=TIER_EDGE, expects_llm=True),
        _case("rec_09", "goi y mon khong cay", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_10", "nen goi mon gi cho tre em", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_11", "suggest something light", wants=True, party=None, solo=False, category="english", tier=TIER_EDGE, expects_llm=True),
        _case("rec_12", "combo cho 2 nguoi", wants=True, party=2, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_13", "mon nao ngon nhat", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_14", "goi y do uong", wants=True, party=None, solo=False, category="clear_recommend", tier=TIER_CORE, expects_llm=False),
        _case("rec_15", "allergy to peanut what can i eat", wants=True, party=None, solo=False, category="allergy_recommend", tier=TIER_EDGE, expects_llm=True),
        # --- Budget ---
        _case("budget_01", "budget 200k goi y", wants=True, party=None, solo=False, category="budget", tier=TIER_CORE, expects_llm=False),
        _case("budget_02", "duoi 150k nguoi goi y", wants=True, party=None, solo=False, category="budget", tier=TIER_CORE, expects_llm=False),
        _case("budget_03", "500k cho 5 nguoi an gi", wants=True, party=5, solo=False, category="budget", tier=TIER_CORE, expects_llm=False),
        _case("budget_04", "tong 800k 6 nguoi goi mon", wants=True, party=6, solo=False, category="budget", tier=TIER_CORE, expects_llm=False),
        _case("budget_05", "toi da 100k goi y mon", wants=True, party=None, solo=False, category="budget", tier=TIER_EDGE, expects_llm=False),
        _case("budget_06", "under 300k per person suggest", wants=True, party=None, solo=False, category="budget", tier=TIER_EDGE, expects_llm=True),
        # --- Catalog browse ---
        _case("catalog_01", "xem menu", wants=False, party=None, solo=False, category="clear_catalog", tier=TIER_CORE, expects_llm=False),
        _case("catalog_02", "thuc don co gi", wants=False, party=None, solo=False, category="clear_catalog", tier=TIER_CORE, expects_llm=False),
        _case("catalog_03", "co mon gi trong menu", wants=False, party=None, solo=False, category="clear_catalog", tier=TIER_EDGE, expects_llm=False),
        _case("catalog_04", "show menu please", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("catalog_05", "list all dishes", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        _case("catalog_06", "co gi trong thuc don", wants=False, party=None, solo=False, category="clear_catalog", tier=TIER_CORE, expects_llm=False),
        # --- Smalltalk ---
        _case("small_01", "alo", wants=False, party=None, solo=False, category="smalltalk", tier=TIER_CORE, expects_llm=True),
        _case("small_02", "cam on nhe", wants=False, party=None, solo=False, category="smalltalk", tier=TIER_CORE, expects_llm=True),
        _case("small_03", "ok vay", wants=False, party=None, solo=False, category="smalltalk", tier=TIER_CORE, expects_llm=True),
        _case("small_04", "chao ban", wants=False, party=None, solo=False, category="smalltalk", tier=TIER_CORE, expects_llm=True),
        _case("small_05", "xin chao", wants=False, party=None, solo=False, category="smalltalk", tier=TIER_CORE, expects_llm=True),
        _case("small_06", "hello", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=True),
        _case("small_07", "tam biet nhe", wants=False, party=None, solo=False, category="smalltalk", tier=TIER_EDGE, expects_llm=True),
        # --- Rejection ---
        _case("reject_01", "khong muon mon do", wants=False, party=None, solo=False, category="rejection", tier=TIER_CORE, expects_llm=True),
        _case("reject_02", "bo qua goi y do", wants=False, party=None, solo=False, category="ambiguous_rejection", tier=TIER_EDGE, expects_llm=True),
        _case("reject_03", "dung goi y nua", wants=False, party=None, solo=False, category="ambiguous_rejection", tier=TIER_EDGE, expects_llm=True),
        _case("reject_04", "no thanks something else", wants=False, party=None, solo=False, category="english", tier=TIER_EDGE, expects_llm=True),
        _case("reject_05", "khong lay mon ay", wants=False, party=None, solo=False, category="rejection", tier=TIER_CORE, expects_llm=True),
        # --- Order / price ---
        _case("order_01", "dat mon pho bo", wants=False, party=None, solo=False, category="clear_order", tier=TIER_CORE, expects_llm=True),
        _case("order_02", "them 2 phan com suon", wants=False, party=None, solo=False, category="clear_order", tier=TIER_CORE, expects_llm=True),
        _case("order_03", "goi mon bun bo luon", wants=False, party=None, solo=False, category="clear_order", tier=TIER_EDGE, expects_llm=True),
        _case("price_01", "pho bo bao nhieu tien", wants=False, party=None, solo=False, category="clear_price", tier=TIER_CORE, expects_llm=False),
        _case("price_02", "gia mon bun bo", wants=False, party=None, solo=False, category="clear_price", tier=TIER_CORE, expects_llm=False),
        _case("price_03", "how much is pho", wants=False, party=None, solo=False, category="english", tier=TIER_CORE, expects_llm=False),
        # --- Service / promo / staff ---
        _case("service_01", "cach dat mon bang qr", wants=False, party=None, solo=False, category="service_info", tier=TIER_CORE, expects_llm=False),
        _case("service_02", "huong dan su dung", wants=False, party=None, solo=False, category="service_info", tier=TIER_EDGE, expects_llm=True),
        _case("promo_01", "khuyen mai hom nay", wants=False, party=None, solo=False, category="promotion_info", tier=TIER_CORE, expects_llm=False),
        _case("promo_02", "co uu dai gi khong", wants=False, party=None, solo=False, category="promotion_info", tier=TIER_CORE, expects_llm=False),
        _case("staff_01", "goi quan ly giup toi", wants=False, party=None, solo=False, category="staff_escalation", tier=TIER_CORE, expects_llm=False),
        _case("staff_02", "gap nhan vien ho tro", wants=False, party=None, solo=False, category="staff_escalation", tier=TIER_CORE, expects_llm=False),
        # --- Occasion ---
        _case("occ_01", "sinh nhat 8 nguoi goi y", wants=True, party=8, solo=False, category="occasion", tier=TIER_CORE, expects_llm=False),
        _case("occ_02", "tiep khach 6 nguoi mon gi", wants=True, party=6, solo=False, category="occasion", tier=TIER_CORE, expects_llm=False),
        # --- Follow-up more dishes ---
        _case(
            "follow_01",
            "con mon khac khong",
            wants=True,
            party=None,
            solo=False,
            category="follow_up_more",
            tier=TIER_MULTI_TURN,
            history=h(("user", "goi y mon chay"), ("assistant", "Mình gợi ý gỏi cuốn chay.")),
            expects_llm=False,
        ),
        _case(
            "follow_02",
            "goi y them mon",
            wants=True,
            party=4,
            solo=False,
            category="follow_up_more",
            tier=TIER_MULTI_TURN,
            history=h(("user", "4 nguoi an gi"), ("assistant", "Với 4 người mình gợi ý lẩu thái.")),
            expects_llm=False,
        ),
        _case(
            "follow_03",
            "mon khac di",
            wants=True,
            party=None,
            solo=False,
            category="follow_up_more",
            tier=TIER_MULTI_TURN,
            history=h(("user", "an gi ngon"), ("assistant", "Thử phở bò ta nhé.")),
            expects_llm=False,
        ),
        # --- Multi-turn context ---
        _case(
            "mt_01",
            "the con mon gi nua",
            wants=True,
            party=4,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "4 nguoi an gi"), ("assistant", "Mình gợi ý lẩu hải sản.")),
            expects_llm=False,
        ),
        _case(
            "mt_02",
            "du cho 4 nguoi khong",
            wants=True,
            party=4,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "4 nguoi an gi"), ("assistant", "Gợi ý combo lẩu + gỏi cuốn.")),
            expects_llm=True,
        ),
        _case(
            "mt_03",
            "wifi thi sao",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_info",
            tier=TIER_MULTI_TURN,
            history=h(("user", "dia chi o dau"), ("assistant", "Quán ở 123 Nguyễn Huệ.")),
            expects_llm=True,
        ),
        _case(
            "mt_04",
            "thanh toan the nao",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_info",
            tier=TIER_MULTI_TURN,
            history=h(("user", "wifi mat khau gi"), ("assistant", "Wifi: CMC2024.")),
            expects_llm=True,
        ),
        _case(
            "mt_05",
            "goi gi cho hop",
            wants=True,
            party=1,
            solo=True,
            category="multi_turn_solo",
            tier=TIER_MULTI_TURN,
            history=h(("user", "toi di mot minh"), ("assistant", "Bạn muốn món nhẹ hay no bụng?")),
            expects_llm=False,
        ),
        _case(
            "mt_06",
            "it cay thoi",
            wants=True,
            party=1,
            solo=True,
            category="multi_turn_solo",
            tier=TIER_MULTI_TURN,
            history=h(("user", "minh an mot minh"), ("assistant", "Mình gợi ý phở gà.")),
            expects_llm=False,
        ),
        _case(
            "mt_07",
            "mon do bao nhieu",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_price",
            tier=TIER_MULTI_TURN,
            history=h(("user", "goi y mon pho"), ("assistant", "Phở bò ta 75k.")),
            expects_llm=True,
        ),
        _case(
            "mt_08",
            "khong an hai san",
            wants=True,
            party=5,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "5 nguoi goi y"), ("assistant", "Gợi ý lẩu cá và gỏi cuốn.")),
            expects_llm=False,
        ),
        # --- Typos / noise ---
        _case("typo_01", "goi y mon chay di", wants=True, party=None, solo=False, category="typo_no_diacritics", tier=TIER_CORE, expects_llm=False),
        _case("typo_02", "8 nguoi an gi hom nay", wants=True, party=8, solo=False, category="typo_no_diacritics", tier=TIER_CORE, expects_llm=False),
        _case("typo_03", "wifi mk gi", wants=False, party=None, solo=False, category="typo_no_diacritics", tier=TIER_CORE, expects_llm=False),
        _case("typo_04", "dia chi o dau vay", wants=False, party=None, solo=False, category="typo_no_diacritics", tier=TIER_CORE, expects_llm=False),
        _case("typo_05", "goi y mon  chay   nhe", wants=True, party=None, solo=False, category="typo_no_diacritics", tier=TIER_EDGE, expects_llm=False),
        _case("typo_06", "4nguoi an gi", wants=True, party=4, solo=False, category="typo_no_diacritics", tier=TIER_EDGE, expects_llm=False),
        # --- Spice-only constraints ---
        _case("spice_01", "khong cay nhe thoi", wants=True, party=None, solo=False, category="spice_constraint", tier=TIER_EDGE, expects_llm=True),
        _case("spice_02", "cay vua goi y mon", wants=True, party=None, solo=False, category="spice_constraint", tier=TIER_CORE, expects_llm=False),
        # --- Mixed edge ---
        _case("edge_01", "an mot minh co ban 2 nguoi khong", wants=False, party=None, solo=False, category="mixed_edge", tier=TIER_EDGE, rationale="Hỏi bàn 2 người, không gợi ý món", expects_llm=True),
        _case("edge_02", "mot minh co duoc khong", wants=False, party=None, solo=False, category="mixed_edge", tier=TIER_EDGE, rationale="Hỏi có được ăn một mình không", expects_llm=True),
        _case("edge_03", "wifi va goi y mon chay", wants=True, party=None, solo=False, category="mixed_edge", tier=TIER_EDGE, rationale="Mixed intent — ưu tiên gợi ý", expects_llm=True),
    ]
    cases.extend(_expand_catalog(h))
    for case in cases:
        if case.get("category") == "english":
            case["language"] = "en"
        elif "language" not in case:
            case["language"] = "vi"
    return cases


def _expand_catalog(h: Any) -> list[dict[str, Any]]:
    """Systematically generated cases for broader routing coverage."""

    cases: list[dict[str, Any]] = []

    party_templates = (
        ("{n} nguoi hom nay an mon gi", True),
        ("cho {n} nguoi goi y mon", True),
        ("nhom {n} nguoi dat gi", True),
        ("{n} khach an trua goi y", True),
    )
    for n in (2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 15):
        for idx, (template, wants) in enumerate(party_templates):
            cases.append(
                _case(
                    f"gen_party_{n:02d}_{idx}",
                    template.format(n=n),
                    wants=wants,
                    party=n,
                    solo=False,
                    category="clear_party",
                    tier=TIER_CORE,
                    expects_llm=False,
                )
            )

    word_party = (
        ("hai nguoi an gi", 2),
        ("ba nguoi goi mon", 3),
        ("tam nguoi an chung", 8),
        ("tu nguoi goi y", 4),
        ("nam nguoi dat ban", 5),
        ("sau nguoi an gi", 6),
        ("bay nguoi goi mon", 7),
        ("tam nguoi tiec", 8),
        ("chin nguoi an trua", 9),
        ("muoi nguoi goi y", 10),
        ("muoi mot nguoi an toi", 11),
        ("bon nguoi dat mon", 4),
    )
    for idx, (message, size) in enumerate(word_party, start=1):
        cases.append(
            _case(
                f"gen_wparty_{idx:02d}",
                message,
                wants=True,
                party=size,
                solo=False,
                category="word_party",
                tier=TIER_EDGE,
            )
        )

    group_social = (
        ("ban be 6 nguoi an gi", 6),
        ("dong nghiep 8 nguoi goi mon", 8),
        ("gia dinh 5 nguoi goi y", 5),
        ("dai gia dinh 12 nguoi", 12),
        ("team building 15 nguoi", 15),
        ("an voi ban 3 nguoi", 3),
    )
    for idx, (message, size) in enumerate(group_social, start=1):
        cases.append(
            _case(
                f"gen_group_{idx:02d}",
                message,
                wants=True,
                party=size,
                solo=False,
                category="group_social",
                tier=TIER_CORE,
                expects_llm=False,
            )
        )

    solo_extra = (
        "di an alone thoi",
        "solo thoi goi gi",
        "chi minh thoi an gi",
        "minh o nha mot minh an gi",
        "tonight im alone suggest food",
        "dining solo any recommendation",
        "1 minh thoi nen goi mon gi",
        "chi co minh minh thoi",
        "khong ai di cung chi minh thoi",
        "em di an mot minh bua toi",
        "tui di mot minh",
        "minh di an 1 minh thoi",
    )
    for idx, message in enumerate(solo_extra, start=1):
        cases.append(
            _case(
                f"gen_solo_{idx:02d}",
                message,
                wants=True,
                party=1,
                solo=True,
                category="ambiguous_solo",
                tier=TIER_EDGE,
                expects_llm=True,
                language="en" if any(w in message for w in ("alone", "solo", "suggest", "dining", "tonight")) else "vi",
            )
        )

    info_extra = (
        "co mang tre em vao khong",
        "tre em co ghe ngoi khong",
        "quy dinh mang do an ngoai",
        "co song khong",
        "nha hang co dieu hoa khong",
        "dat ban truoc nhu the nao",
        "co giao hang khong",
        "ship do an duoc khong",
        "co menu tieng anh khong",
        "cho khach nuoc ngoai o dau",
        "do uong co ban khong",
        "co ban bar khong",
        "faq ve dat mon",
        "chinh sach huy don",
    )
    for idx, message in enumerate(info_extra, start=1):
        cases.append(
            _case(
                f"gen_info_{idx:02d}",
                message,
                wants=False,
                party=None,
                solo=False,
                category="clear_info",
                tier=TIER_CORE,
                expects_llm=False,
            )
        )

    allergy_cases = (
        ("di ung tom goi y mon gi", True, None),
        ("khong an duoc dau phong", True, None),
        ("allergic to peanuts recommend", True, None),
        ("tranh gluten goi y gi", True, None),
        ("khong an thit bo goi y", True, None),
        ("vegan options please", True, None),
        ("thuan chay co mon gi", True, None),
        ("halal food suggestions", True, None),
        ("khong an oc goi y gi", True, None),
        ("tre em di ung hai san", True, None),
        ("khach khong an duoc cua", True, None),
        ("shellfish allergy what is safe", True, None),
    )
    for idx, (message, wants, party) in enumerate(allergy_cases, start=1):
        cases.append(
            _case(
                f"gen_allergy_{idx:02d}",
                message,
                wants=wants,
                party=party,
                solo=False,
                category="allergy_recommend",
                tier=TIER_EDGE if "goi y" not in message and "recommend" not in message else TIER_CORE,
                expects_llm="goi y" not in message and "recommend" not in message and "suggest" not in message,
                language="en" if message.isascii() else "vi",
            )
        )

    dietary_amb = (
        "an keto duoc gi",
        "mon low carb",
        "it dam protein cao",
        "an kieng giam can goi y",
        "mon chay khong nam",
        "healthy options",
        "mon it calo",
        "diet menu co gi",
    )
    for idx, message in enumerate(dietary_amb, start=1):
        cases.append(
            _case(
                f"gen_diet_{idx:02d}",
                message,
                wants=True,
                party=None,
                solo=False,
                category="ambiguous_dietary",
                tier=TIER_EDGE,
                expects_llm=True,
                language="en" if message.isascii() else "vi",
            )
        )

    rec_extra = (
        "goi y mon man",
        "mon khai vi nao ngon",
        "do uong gi hop",
        "mon trang mieng ngon",
        "combo cho cap doi",
        "mon an sang goi y",
        "mon phu hop tre em",
        "goi y mon dac san",
        "best seller la gi",
        "mon noi bat hom nay",
    )
    for idx, message in enumerate(rec_extra, start=1):
        cases.append(
            _case(
                f"gen_rec_{idx:02d}",
                message,
                wants=True,
                party=None,
                solo=False,
                category="clear_recommend",
                tier=TIER_CORE,
                expects_llm=False,
            )
        )

    catalog_extra = (
        "cac mon pho co gi",
        "mon lau trong menu",
        "co mon hai san khong",
        "danh sach mon chay",
        "browse appetizers",
        "what is on the menu",
        "show me rice dishes",
        "mon com co nhung gi",
    )
    for idx, message in enumerate(catalog_extra, start=1):
        cases.append(
            _case(
                f"gen_catalog_{idx:02d}",
                message,
                wants=False,
                party=None,
                solo=False,
                category="clear_category",
                tier=TIER_CORE,
                expects_llm=False,
                language="en" if message.isascii() else "vi",
            )
        )

    english_extra = (
        ("how do i pay", False, None, "clear_info", False),
        ("table for six please", True, 6, "clear_party", False),
        ("recommend spicy dishes", True, None, "clear_recommend", True),
        ("I am alone what should I order", True, 1, "ambiguous_solo", True),
        ("no seafood please suggest", True, None, "allergy_recommend", True),
        ("stop suggesting that", False, None, "ambiguous_rejection", True),
        ("thanks bye", False, None, "smalltalk", True),
        ("add two pho to cart", False, None, "clear_order", True),
        ("price of spring rolls", False, None, "clear_price", False),
        ("any promotions today", False, None, "promotion_info", False),
    )
    for idx, (message, wants, party, category, expects_llm) in enumerate(english_extra, start=1):
        cases.append(
            _case(
                f"gen_en_{idx:02d}",
                message,
                wants=wants,
                party=party,
                solo=party == 1,
                category=category,
                tier=TIER_EDGE if expects_llm else TIER_CORE,
                expects_llm=expects_llm,
                language="en",
            )
        )

    reject_extra = (
        "thoi dung goi y nua",
        "bo qua mon do di",
        "skip that suggestion",
        "khong thich goi y do",
        "something else please",
        "mon khac di dung goi y cu",
    )
    for idx, message in enumerate(reject_extra, start=1):
        cases.append(
            _case(
                f"gen_reject_{idx:02d}",
                message,
                wants=False,
                party=None,
                solo=False,
                category="ambiguous_rejection",
                tier=TIER_EDGE,
                expects_llm=True,
                language="en" if message.isascii() else "vi",
            )
        )

    multi_turn_extra: list[dict[str, Any]] = [
        _case(
            "gen_mt_01",
            "con mon nao khac",
            wants=True,
            party=6,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "6 nguoi an gi"), ("assistant", "Gợi ý lẩu bò.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_02",
            "it hon cay",
            wants=True,
            party=4,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "4 nguoi goi y"), ("assistant", "Thử bún bò Huế.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_03",
            "du tien khong",
            wants=True,
            party=5,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "500k cho 5 nguoi"), ("assistant", "Combo lẩu + gỏi cuốn khoảng 480k.")),
            expects_llm=True,
        ),
        _case(
            "gen_mt_04",
            "dia chi thi sao",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_info",
            tier=TIER_MULTI_TURN,
            history=h(("user", "gio mo cua"), ("assistant", "Mở 10h-22h.")),
            expects_llm=True,
        ),
        _case(
            "gen_mt_05",
            "gui xe the nao",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_info",
            tier=TIER_MULTI_TURN,
            history=h(("user", "dia chi o dau"), ("assistant", "123 Nguyễn Huệ.")),
            expects_llm=True,
        ),
        _case(
            "gen_mt_06",
            "mon nhe thoi",
            wants=True,
            party=1,
            solo=True,
            category="multi_turn_solo",
            tier=TIER_MULTI_TURN,
            history=h(("user", "di an solo toi nay"), ("assistant", "Bạn thích món nước hay món khô?")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_07",
            "khong an tom",
            wants=True,
            party=1,
            solo=True,
            category="multi_turn_solo",
            tier=TIER_MULTI_TURN,
            history=h(("user", "toi di mot minh"), ("assistant", "Gợi ý phở gà.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_08",
            "goi y them",
            wants=True,
            party=8,
            solo=False,
            category="follow_up_more",
            tier=TIER_MULTI_TURN,
            history=h(("user", "8 nguoi an gi"), ("assistant", "Lẩu hải sản và mẹt chiên.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_09",
            "nao khac di",
            wants=True,
            party=3,
            solo=False,
            category="follow_up_more",
            tier=TIER_MULTI_TURN,
            history=h(("user", "3 nguoi nen goi mon gi"), ("assistant", "Gợi ý cơm sườn.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_10",
            "bao nhieu vay",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_price",
            tier=TIER_MULTI_TURN,
            history=h(("user", "goi y mon pho"), ("assistant", "Phở bò 75k.")),
            expects_llm=True,
        ),
        _case(
            "gen_mt_11",
            "tom cua co khong",
            wants=True,
            party=4,
            solo=False,
            category="multi_turn_allergy",
            tier=TIER_MULTI_TURN,
            history=h(("user", "4 nguoi an gi"), ("assistant", "Gợi ý lẩu và gỏi.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_12",
            "tre em co mon gi",
            wants=True,
            party=4,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "ca nha 4 nguoi"), ("assistant", "Gợi ý phở và gỏi cuốn.")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_13",
            "the con tra bang the duoc khong",
            wants=False,
            party=None,
            solo=False,
            category="multi_turn_info",
            tier=TIER_MULTI_TURN,
            history=h(("user", "mon do ngon qua"), ("assistant", "Cảm ơn bạn.")),
            expects_llm=True,
        ),
        _case(
            "gen_mt_14",
            "ok goi y di",
            wants=True,
            party=2,
            solo=False,
            category="multi_turn_party",
            tier=TIER_MULTI_TURN,
            history=h(("user", "2 nguoi an gi"), ("assistant", "Bạn muốn món nước hay cơm?")),
            expects_llm=False,
        ),
        _case(
            "gen_mt_15",
            "khong lay mon do",
            wants=False,
            party=2,
            solo=False,
            category="multi_turn_rejection",
            tier=TIER_MULTI_TURN,
            history=h(("user", "2 nguoi an gi"), ("assistant", "Gợi ý lẩu cá.")),
            expects_llm=True,
        ),
    ]
    cases.extend(multi_turn_extra)

    edge_extra = (
        ("co ban cho 1 nguoi khong", False, None, "Hỏi chỗ ngồi"),
        ("mot minh ngoi bar duoc khong", False, None, "Hỏi bar solo"),
        ("goi y va cho dia chi", True, None, "Mixed — ưu tiên gợi ý"),
        ("wifi roi goi y mon", True, None, "Mixed FAQ + gợi ý"),
        ("8 nguoi nhung co nguoi an chay", True, 8, "Party + dietary"),
        ("2 nguoi 1 nguoi an chay", True, 2, "Party nhỏ + chay"),
        ("khong phai goi y dau chi hoi gia", False, None, "Phủ định gợi ý"),
    )
    for idx, (message, wants, party, rationale) in enumerate(edge_extra, start=1):
        cases.append(
            _case(
                f"gen_edge_{idx:02d}",
                message,
                wants=wants,
                party=party,
                solo=False,
                category="mixed_edge",
                tier=TIER_EDGE,
                rationale=rationale,
                expects_llm=True,
            )
        )

    noisy = (
        "  alo   ban  oi  ",
        "wifi??? mat khau",
        "4  nguoi   an   gi",
        "dia chi... o dau",
    )
    for idx, message in enumerate(noisy, start=1):
        stripped = " ".join(message.split()).casefold()
        wants = "goi y" in stripped or ("an gi" in stripped and "menu" not in stripped)
        party = 4 if "4" in stripped and "nguoi" in stripped else None
        category = "noisy_input" if idx != 1 else "smalltalk"
        expects = True if idx == 1 else (wants and party is None)
        if idx == 1:
            wants = False
            party = None
        cases.append(
            _case(
                f"gen_noisy_{idx:02d}",
                message.strip(),
                wants=wants,
                party=party,
                solo=False,
                category=category,
                tier=TIER_EDGE,
                expects_llm=expects,
            )
        )

    return cases


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_messages: set[str] = set()
    for index, case in enumerate(cases, start=1):
        for field in REQUIRED_FIELDS:
            if field not in case:
                issues.append(f"Case #{index} ({case.get('id', '?')}): missing `{field}`")
        case_id = str(case.get("id", ""))
        if case_id in seen_ids:
            issues.append(f"Duplicate id: {case_id}")
        seen_ids.add(case_id)
        message_key = str(case.get("message", "")).strip().casefold()
        if message_key in seen_messages:
            issues.append(f"Duplicate message: {case_id!r} -> {case.get('message')!r}")
        seen_messages.add(message_key)
        party = case.get("expected_party_size")
        if party is not None and not isinstance(party, int):
            issues.append(f"{case_id}: expected_party_size must be int or null")
        if case.get("expected_is_solo_dining") and party not in (1, None):
            issues.append(f"{case_id}: solo=true usually implies party_size=1 or null")
    return issues
