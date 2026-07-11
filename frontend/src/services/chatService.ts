import { getApiBaseUrl } from "./apiClient";
import type {
  CreateChatSessionRequest,
  CreateChatSessionResponse,
  SendChatMessageRequest,
  SendChatMessageResponse,
} from "../types";

async function postJson<TResponse>(path: string, body?: unknown, accessToken?: string): Promise<TResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { "X-Chat-Session-Token": accessToken } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

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
    accessToken: string,
  ): Promise<SendChatMessageResponse> {
    return postJson<SendChatMessageResponse>(
      `/chat/sessions/${chatSessionId}/messages`,
      request,
      accessToken,
    );
  },
};
