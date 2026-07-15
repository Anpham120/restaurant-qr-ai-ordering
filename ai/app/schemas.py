from __future__ import annotations

from pydantic import BaseModel, Field


class ChatHistorySuggestedAction(BaseModel):
    menu_item_id: str
    name: str | None = None


class ChatHistoryItem(BaseModel):
    role: str = Field(default="user")
    content: str
    suggested_cart_actions: list[ChatHistorySuggestedAction] = Field(default_factory=list)


class MenuItemContext(BaseModel):
    id: str
    name: str
    category_id: str | None = None
    category_name: str | None = None
    description: str | None = None
    price_vnd: float | int | None = None
    tags: list[str] = Field(default_factory=list)
    is_available: bool = True


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = Field(default_factory=list)
    session_memory: str = ""
    rolling_summary: str = ""
    session_id: str = ""
    menu_version: str = ""
    excluded_menu_item_ids: list[str] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    cart_items: list[dict] = Field(default_factory=list)
    orders: list[dict] = Field(default_factory=list)
    promotions: list[dict] = Field(default_factory=list)
    local_time: str | None = None
    meal_period: str | None = None
    menu_items: list[MenuItemContext] = Field(default_factory=list)
    table_code: str | None = None


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


class FollowUp(BaseModel):
    can_show_more: bool = False
    remaining_count: int = 0


class ChatResponse(BaseModel):
    content: str
    provider_available: bool
    model: str
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    guardrail_flags: list[str] = Field(default_factory=list)
    suggested_cart_actions: list[SuggestedCartAction] = Field(default_factory=list)
    follow_up: FollowUp = Field(default_factory=FollowUp)
    suggest_staff_handoff: bool = False
