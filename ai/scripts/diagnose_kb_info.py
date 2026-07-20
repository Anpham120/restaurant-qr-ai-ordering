import asyncio
import sys

from app.config import load_config
from app.services.assistant import AiAssistantService

QUERIES = [
    ("wifi_pass", "mat khau wifi tai nha hang la gi"),
    ("hours", "gio mo cua nha hang"),
    ("parking", "co cho gui xe khong"),
    ("payment", "thanh toan bang gi"),
    ("goi_kids", "co mon goi nao cho tre con an khong"),
    ("address", "nha hang o dau"),
    ("vip", "co phong vip khong"),
    ("birthday", "co to chuc sinh nhat khong"),
]


async def main() -> None:
    service = AiAssistantService(load_config())
    service.prewarm()
    menu_items = [
        {
            "id": "m_001",
            "name": "Goi cuon tom thit",
            "category_name": "Khai vi",
            "price_vnd": 65000,
            "is_available": True,
            "tags": ["tre em"],
        },
        {
            "id": "m_002",
            "name": "Goi cuon chay",
            "category_name": "Khai vi",
            "price_vnd": 45000,
            "is_available": True,
            "tags": ["chay"],
        },
    ]

    for label, message in QUERIES:
        response, _ = await service._process_chat(
            {"message": message, "history": [], "menu_items": menu_items}
        )
        content = response.get("content", "")
        denies = any(
            phrase in content.lower()
            for phrase in ("chua co", "chưa có", "chua thay", "chưa thấy", "chua du")
        )
        print(label, response.get("model"), "denies=", denies, "len=", len(content))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
