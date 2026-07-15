export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  suggestedCartActions?: SuggestedCartAction[];
};

export type SuggestedCartAction = {
  menuItemId: string;
  name: string;
  price: number;
  quantity: number;
  reason: string;
  requiresCustomerConfirmation: true;
  status?: "pending" | "confirmed" | "dismissed";
  evidenceIds?: string[];
};

export type ChatRecommendation = {
  menuItemId: string;
  status: string;
  turnId?: string;
  updatedAt: string;
};

export type ChatGuardrailFlag =
  | "AI_PROVIDER_UNAVAILABLE"
  | "MENU_ITEM_NOT_FOUND"
  | "MENU_ITEM_UNAVAILABLE"
  | "OUT_OF_SCOPE"
  | "CUSTOMER_CONFIRMATION_REQUIRED";

export type CreateChatSessionResponse = {
  chatSessionId: string;
  createdAt: string;
  updatedAt: string;
  accessToken: string;
  reused: boolean;
  messages: ChatMessage[];
  recommendations: ChatRecommendation[];
};

export type CreateChatSessionRequest = {
  tableSessionId?: string;
  tableCode?: string;
};

export type SendChatMessageRequest = {
  content: string;
  tableCode?: string;
};

export type SendChatMessageResponse = {
  userMessage: ChatMessage;
  message: ChatMessage;
  suggestedCartActions: SuggestedCartAction[];
  guardrailFlags: ChatGuardrailFlag[];
  suggestStaffHandoff?: boolean;
  followUp?: { canShowMore: boolean; remainingCount: number };
};

export type ChatHistoryResponse = {
  chatSessionId: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  recommendations: ChatRecommendation[];
};
