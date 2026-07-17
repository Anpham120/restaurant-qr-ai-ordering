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

  async sendMessageStream(
    chatSessionId: string,
    request: SendChatMessageRequest,
    accessToken: string,
    handlers: {
      onToken: (text: string) => void;
      onFinal: (response: SendChatMessageResponse) => void;
      onError?: (error: Error) => void;
    },
  ): Promise<boolean> {
    const response = await fetch(
      `${getApiBaseUrl()}/chat/sessions/${encodeURIComponent(chatSessionId)}/messages/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Chat-Session-Token": accessToken,
        },
        body: JSON.stringify(request),
      },
    );

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

    if (!response.body) {
      throw new ChatApiError(500, "STREAM_UNAVAILABLE", "Streaming body is unavailable.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    let receivedFinal = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const rawEvent of events) {
        const lines = rawEvent.split("\n");
        let eventName = "";
        let dataLine = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventName = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            dataLine = line.slice(6);
          }
        }

        if (!eventName || !dataLine) {
          continue;
        }

        const payload = JSON.parse(dataLine) as Record<string, unknown>;
        if (eventName === "token" && typeof payload.text === "string") {
          handlers.onToken(payload.text);
        } else if (eventName === "final") {
          receivedFinal = true;
          handlers.onFinal(payload as SendChatMessageResponse);
        } else if (eventName === "done" && handlers.onError && !payload.ok) {
          handlers.onError(new Error("Stream ended unexpectedly."));
        }
      }
    }

    return receivedFinal;
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
