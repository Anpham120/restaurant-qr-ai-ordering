export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
};

export type SuggestedCartAction = {
  menuItemId: string;
  name: string;
  price: number;
  quantity: number;
  reason: string;
  requiresCustomerConfirmation: true;
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
  message: ChatMessage;
  suggestedCartActions: SuggestedCartAction[];
  guardrailFlags: ChatGuardrailFlag[];
};
