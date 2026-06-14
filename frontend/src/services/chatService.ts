import { getApiBaseUrl } from "./apiClient";
import { getCustomerMenu } from "./menuService";
import type {
  CreateChatSessionResponse,
  SendChatMessageRequest,
  SendChatMessageResponse,
  SuggestedCartAction,
} from "../types";

const useMockChat = import.meta.env.VITE_USE_MOCK_CHAT === "true";

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function createId(prefix: string) {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

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

async function buildSuggestedAction(): Promise<SuggestedCartAction | null> {
  const menu = await getCustomerMenu();
  const item =
    menu.items.find((menuItem) => menuItem.isAvailable && menuItem.tags.includes("fresh")) ??
    menu.items.find((menuItem) => menuItem.isAvailable);

  if (!item) {
    return null;
  }

  return {
    menuItemId: item.id,
    name: item.name,
    price: item.price,
    quantity: 1,
    reason: "Món còn bán, phù hợp để bắt đầu bữa ăn và khách cần xác nhận trước khi thêm vào giỏ.",
    requiresCustomerConfirmation: true,
  };
}

async function buildMockResponse(request: SendChatMessageRequest): Promise<SendChatMessageResponse> {
  const content = request.content.toLowerCase();
  const createdAt = new Date().toISOString();

  if (content.includes("python") || content.includes("code")) {
    return {
      message: {
        id: createId("msg"),
        role: "assistant",
        content:
          "Mình chỉ hỗ trợ chọn món, giải đáp menu và gợi ý giỏ hàng cho CMC Restaurant. Bạn muốn món nhẹ, món chính hay đồ uống?",
        createdAt,
      },
      suggestedCartActions: [],
      guardrailFlags: ["OUT_OF_SCOPE"],
    };
  }

  if (content.includes("pizza") || content.includes("không có")) {
    return {
      message: {
        id: createId("msg"),
        role: "assistant",
        content:
          "Mình chưa thấy món đó trong menu hiện tại nên sẽ không tự bịa món hoặc giá. Bạn có thể hỏi món chính, khai vị, hải sản hoặc đồ uống đang có.",
        createdAt,
      },
      suggestedCartActions: [],
      guardrailFlags: ["MENU_ITEM_NOT_FOUND"],
    };
  }

  const suggestedAction = await buildSuggestedAction();

  if (!suggestedAction) {
    return {
      message: {
        id: createId("msg"),
        role: "assistant",
        content:
          "Hiện tại mình chưa tìm được món còn bán phù hợp. Bạn vẫn có thể xem thực đơn để chọn trực tiếp.",
        createdAt,
      },
      suggestedCartActions: [],
      guardrailFlags: ["MENU_ITEM_UNAVAILABLE"],
    };
  }

  return {
    message: {
      id: createId("msg"),
      role: "assistant",
      content: `Mình gợi ý ${suggestedAction.name}. Giá hiện tại là ${suggestedAction.price.toLocaleString("vi-VN")} VND. Mình chỉ đề xuất, bạn cần bấm xác nhận nếu muốn thêm món vào giỏ.`,
      createdAt,
    },
    suggestedCartActions: [suggestedAction],
    guardrailFlags: ["CUSTOMER_CONFIRMATION_REQUIRED"],
  };
}

export const chatApi = {
  async createSession(): Promise<CreateChatSessionResponse> {
    if (!useMockChat) {
      return postJson<CreateChatSessionResponse>("/chat/sessions");
    }

    await wait(240);

    return {
      chatSessionId: createId("chat"),
      createdAt: new Date().toISOString(),
    };
  },

  async sendMessage(
    chatSessionId: string,
    request: SendChatMessageRequest,
  ): Promise<SendChatMessageResponse> {
    if (!useMockChat) {
      return postJson<SendChatMessageResponse>(
        `/chat/sessions/${chatSessionId}/messages`,
        request,
      );
    }

    await wait(760);
    return buildMockResponse(request);
  },
};
