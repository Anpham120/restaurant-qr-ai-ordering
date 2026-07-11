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
};

export type ChatGuardrailFlag =
  | "AI_SERVICE_UNAVAILABLE"
  | "AI_OUTPUT_POLICY_VIOLATION"
  | "PROMPT_INJECTION_BLOCKED"
  | "MENU_ITEM_NOT_FOUND"
  | "MENU_ITEM_UNAVAILABLE"
  | "OUT_OF_SCOPE"
  | "CUSTOMER_CONFIRMATION_REQUIRED";

export type CreateChatSessionResponse = {
  chatSessionId: string;
  createdAt: string;
  updatedAt: string;
  reused: boolean;
  messages: ChatMessage[];
};

export type CreateChatSessionRequest = {
  tableSessionId?: string;
  tableCode?: string;
};

export type SendChatMessageRequest = {
  content: string;
};

export type RetrievedSource = {
  source: string;
  title: string;
  score: number;
};

export type ChatDiagnostics = {
  aiServiceAvailable: boolean;
  llmProviderAvailable: boolean;
  model: string;
  retrievalMethod: string;
  fastPath?: string | null;
  latencyMs: Record<string, number>;
  retrievedSources: RetrievedSource[];
};

export type SendChatMessageResponse = {
  message: ChatMessage;
  suggestedCartActions: SuggestedCartAction[];
  guardrailFlags: ChatGuardrailFlag[];
  diagnostics: ChatDiagnostics;
};

export type ChatHistoryResponse = {
  chatSessionId: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
};
