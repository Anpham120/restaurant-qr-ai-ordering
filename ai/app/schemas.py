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


class RetrievedSource(BaseModel):
    source: str
    title: str
    score: float


class SuggestedCartAction(BaseModel):
    menu_item_id: str
    name: str
    price_vnd: float | int | None = None
    quantity: int = Field(default=1, ge=1, le=20)
    reason: str | None = None
    requires_customer_confirmation: bool = True


class ChatResponse(BaseModel):
    content: str
    provider_available: bool
    model: str
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    guardrail_flags: list[str] = Field(default_factory=list)
    suggested_cart_actions: list[SuggestedCartAction] = Field(default_factory=list)
