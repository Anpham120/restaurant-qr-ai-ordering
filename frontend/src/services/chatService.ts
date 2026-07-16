import { getApiBaseUrl } from "./apiClient";
import type {
  ChatHistoryResponse,
  ChatRecommendation,
  CreateChatSessionRequest,
  CreateChatSessionResponse,
  SendChatMessageRequest,
  SendChatMessageResponse,
} from "../types";

type ChatApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class ChatApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function requestJson<TResponse>(
  path: string,
  method: "GET" | "POST",
  body?: unknown,
  accessToken?: string,
): Promise<TResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(accessToken ? { "X-Chat-Session-Token": accessToken } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let errorBody: ChatApiErrorBody | null = null;
    try {
      errorBody = await response.json() as ChatApiErrorBody;
    } catch {
      errorBody = null;
    }

    throw new ChatApiError(
      response.status,
      errorBody?.error?.code ?? `HTTP_${response.status}`,
      errorBody?.error?.message ?? "Không thể kết nối tới dịch vụ tư vấn.",
    );
  }

  return (await response.json()) as TResponse;
}

export const chatApi = {
  async createSession(request?: CreateChatSessionRequest): Promise<CreateChatSessionResponse> {
    return requestJson<CreateChatSessionResponse>("/chat/sessions", "POST", request);
  },

  async sendMessage(
    chatSessionId: string,
    request: SendChatMessageRequest,
    accessToken: string,
  ): Promise<SendChatMessageResponse> {
    return requestJson<SendChatMessageResponse>(
      `/chat/sessions/${encodeURIComponent(chatSessionId)}/messages`,
      "POST",
      request,
      accessToken,
    );
  },

  async getHistory(chatSessionId: string, accessToken: string): Promise<ChatHistoryResponse> {
    return requestJson<ChatHistoryResponse>(
      `/chat/sessions/${encodeURIComponent(chatSessionId)}/messages`,
      "GET",
      undefined,
      accessToken,
    );
  },

  async updateRecommendation(
    chatSessionId: string,
    request: { menuItemId: string; status: string; turnId?: string },
    accessToken: string,
  ): Promise<ChatRecommendation[]> {
    return requestJson<ChatRecommendation[]>(
      `/chat/sessions/${encodeURIComponent(chatSessionId)}/recommendations`,
      "POST",
      request,
      accessToken,
    );
  },

  async submitFeedback(
    chatSessionId: string,
    request: { messageId: string; rating: "up" | "down"; reason?: string },
    accessToken: string,
  ): Promise<{ ok: boolean }> {
    return requestJson<{ ok: boolean }>(
      `/chat/sessions/${encodeURIComponent(chatSessionId)}/feedback`,
      "POST",
      request,
      accessToken,
    );
  },

  async requestAssistance(
    chatSessionId: string,
    request: { note?: string },
    accessToken: string,
  ): Promise<{ ok: boolean; tableCode: string }> {
    return requestJson<{ ok: boolean; tableCode: string }>(
      `/chat/sessions/${encodeURIComponent(chatSessionId)}/assistance`,
      "POST",
      request,
      accessToken,
    );
  },
};
