from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


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
    calories_kcal: float | int | None = None
    sugar_g: float | int | None = None
    protein_g: float | int | None = None
    ingredients: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    nutrition_facts: dict[str, Any] = Field(default_factory=dict)


class PendingClarification(BaseModel):
    slot: str
    question: str = ""
    candidate_menu_item_ids: list[str] = Field(default_factory=list)


class ConversationFrame(BaseModel):
    active_topic: str | None = None
    active_intent: str | None = None
    focus_menu_item_ids: list[str] = Field(default_factory=list)
    resolved_category: str | None = None
    resolved_tags: list[str] = Field(default_factory=list)
    turn_sequence: int = Field(default=0, ge=0)
    pending_clarification: PendingClarification | None = None
    constraint_provenance: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SessionState(BaseModel):
    facts: list[dict[str, Any]] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    referenced_menu_item_ids: list[str] = Field(default_factory=list)
    suggested_menu_item_ids: list[str] = Field(default_factory=list)
    rejected_menu_item_ids: list[str] = Field(default_factory=list)
    accepted_menu_item_ids: list[str] = Field(default_factory=list)
    added_to_cart_menu_item_ids: list[str] = Field(default_factory=list)
    rolling_summary: str = ""
    memory_version: str = "v1"
    conversation_frame: ConversationFrame = Field(default_factory=ConversationFrame)


class LiveContext(BaseModel):
    catalog_version: str = ""
    menu_items: list[MenuItemContext] = Field(default_factory=list)
    cart_items: list[dict[str, Any]] = Field(default_factory=list)
    orders: list[dict[str, Any]] = Field(default_factory=list)
    promotions: list[dict[str, Any]] = Field(default_factory=list)
    local_time: str | None = None
    meal_period: str | None = None
    table_code: str | None = None


class ChatRequest(BaseModel):
    contract_version: str = "v1"
    message: str
    history: list[ChatHistoryItem] = Field(default_factory=list)
    session_memory: str = ""
    rolling_summary: str = ""
    session_id: str = ""
    menu_version: str = ""
    catalog_version: str = ""
    session_state: SessionState = Field(default_factory=SessionState)
    live_context: LiveContext = Field(default_factory=LiveContext)
    excluded_menu_item_ids: list[str] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    cart_items: list[dict] = Field(default_factory=list)
    orders: list[dict] = Field(default_factory=list)
    promotions: list[dict] = Field(default_factory=list)
    local_time: str | None = None
    meal_period: str | None = None
    menu_items: list[MenuItemContext] = Field(default_factory=list)
    table_code: str | None = None
    pipeline_profile: str = "llm_first_v1"

    @model_validator(mode="after")
    def normalize_v2_payload(self) -> "ChatRequest":
        if self.contract_version == "v2" and len(self.history) > 12:
            raise ValueError("ChatRequestV2.history accepts at most 12 turns")
        if self.live_context.catalog_version and not self.catalog_version:
            self.catalog_version = self.live_context.catalog_version
        if self.catalog_version and not self.menu_version:
            self.menu_version = self.catalog_version
        if self.live_context.menu_items and not self.menu_items:
            self.menu_items = self.live_context.menu_items
        if self.live_context.cart_items and not self.cart_items:
            self.cart_items = self.live_context.cart_items
        if self.live_context.orders and not self.orders:
            self.orders = self.live_context.orders
        if self.live_context.promotions and not self.promotions:
            self.promotions = self.live_context.promotions
        if self.live_context.local_time and not self.local_time:
            self.local_time = self.live_context.local_time
        if self.live_context.meal_period and not self.meal_period:
            self.meal_period = self.live_context.meal_period
        if self.live_context.table_code and not self.table_code:
            self.table_code = self.live_context.table_code
        if self.session_state.rolling_summary and not self.rolling_summary:
            self.rolling_summary = self.session_state.rolling_summary
        if self.session_state.facts and not self.facts:
            self.facts = self.session_state.facts
        return self


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievedSource(BaseModel):
    source: str
    title: str
    score: float
    chunk_id: str | None = None
    document_id: str | None = None
    section_path: list[str] = Field(default_factory=list)


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


class DecisionTrace(BaseModel):
    intent: str | None = None
    route: str | None = None
    confidence: float | None = None
    evidence_sufficient: bool | None = None
    abstain_reason: str | None = None


class EvidenceReference(BaseModel):
    source: str
    title: str | None = None
    chunk_id: str | None = None
    menu_item_id: str | None = None
    section: str | None = None
    score: float | None = None


class VerifiedClaim(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    verified: bool = False
    reason: str | None = None


class RetrieverRuntime(BaseModel):
    requested_method: str
    effective_method: str
    embedding_model: str | None = None
    fallback_used: bool = False
    fallback_error_type: str | None = None


class SessionUpdates(BaseModel):
    facts: list[dict[str, Any]] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    referenced_menu_item_ids: list[str] = Field(default_factory=list)
    suggested_menu_item_ids: list[str] = Field(default_factory=list)
    rejected_menu_item_ids: list[str] = Field(default_factory=list)
    accepted_menu_item_ids: list[str] = Field(default_factory=list)
    added_to_cart_menu_item_ids: list[str] = Field(default_factory=list)
    rolling_summary: str | None = None
    memory_version: str = "v1"
    conversation_frame: ConversationFrame = Field(default_factory=ConversationFrame)


class ChatResponse(BaseModel):
    contract_version: str = "v2"
    content: str
    provider_available: bool
    provider_status: str = "not_called"
    model: str
    pipeline_version: str = "v2"
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    decision: DecisionTrace = Field(default_factory=DecisionTrace)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    claims: list[VerifiedClaim] = Field(default_factory=list)
    retriever_runtime: RetrieverRuntime | None = None
    session_updates: SessionUpdates = Field(default_factory=SessionUpdates)
    guardrail_flags: list[str] = Field(default_factory=list)
    suggested_cart_actions: list[SuggestedCartAction] = Field(default_factory=list)
    follow_up: FollowUp = Field(default_factory=FollowUp)
    suggest_staff_handoff: bool = False
    latency_ms: dict[str, float | str] = Field(default_factory=dict)
    updated_rolling_summary: str | None = None
    pipeline_profile: str = "llm_first_v1"
    resolved_menu_item_ids: list[str] = Field(default_factory=list)
    verifier_result: str = "not_applicable"
