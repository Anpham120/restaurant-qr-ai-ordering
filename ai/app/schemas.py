from __future__ import annotations

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: str = Field(default="user")
    content: str


class MenuItemContext(BaseModel):
    id: str
    name: str
    category_id: str | None = None
    description: str | None = None
    price_vnd: float | int | None = None
    tags: list[str] = Field(default_factory=list)
    is_available: bool = True


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = Field(default_factory=list)
    menu_items: list[MenuItemContext] = Field(default_factory=list)


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=10)
