import { getApiBaseUrl } from "./apiClient";
import type {
  CreateChatSessionRequest,
  CreateChatSessionResponse,
  ChatHistoryResponse,
  SendChatMessageRequest,
  SendChatMessageResponse,
} from "../types";

async function postJson<TResponse>(path: string, body?: unknown): Promise<TResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`Chat API failed with HTTP ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`);
  if (!response.ok) {
    throw new Error(`Chat API failed with HTTP ${response.status}`);
  }
  return (await response.json()) as TResponse;
}

export const chatApi = {
  async createSession(request?: CreateChatSessionRequest): Promise<CreateChatSessionResponse> {
    return postJson<CreateChatSessionResponse>("/chat/sessions", request);
  },

  async sendMessage(
    chatSessionId: string,
    request: SendChatMessageRequest,
  ): Promise<SendChatMessageResponse> {
    return postJson<SendChatMessageResponse>(
      `/chat/sessions/${chatSessionId}/messages`,
      request,
    );
  },

  async getHistory(chatSessionId: string): Promise<ChatHistoryResponse> {
    return getJson<ChatHistoryResponse>(`/chat/sessions/${chatSessionId}/messages`);
  },
};
