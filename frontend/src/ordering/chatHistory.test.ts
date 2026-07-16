import { describe, expect, it } from "vitest";
import type { ChatMessage } from "../types";
import { appendCommittedExchange, restoreCommittedHistory } from "./chatHistory";

const welcome: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content: "Xin chào",
  createdAt: "2026-07-13T00:00:00Z",
};

describe("chat history lifecycle", () => {
  it("TestV26_only appends the server-confirmed exchange", () => {
    const userMessage: ChatMessage = {
      id: "msg_user",
      role: "user",
      content: "Tôi muốn món thanh mát",
      createdAt: "2026-07-13T00:01:00Z",
    };
    const assistantMessage: ChatMessage = {
      id: "msg_ai",
      role: "assistant",
      content: "Bạn có thể chọn nước ép.",
      createdAt: "2026-07-13T00:01:01Z",
    };

    expect(appendCommittedExchange([welcome], {
      userMessage,
      message: assistantMessage,
    })).toEqual([welcome, userMessage, assistantMessage]);
  });

  it("TestV25_restores committed server history after refresh", () => {
    const persisted = [{ ...welcome, id: "persisted" }];

    expect(restoreCommittedHistory(persisted, welcome)).toEqual(persisted);
    expect(restoreCommittedHistory([], welcome)).toEqual([welcome]);
  });

  it("TestV37_restores persisted recommendation cards with the assistant message", () => {
    const assistantWithCard: ChatMessage = {
      id: "msg_ai_card",
      role: "assistant",
      content: "Mình gợi ý Cua rang me.",
      createdAt: "2026-07-13T00:02:00Z",
      suggestedCartActions: [{
        menuItemId: "m_025",
        name: "Cua rang me",
        price: 380000,
        quantity: 1,
        reason: "Món còn bán.",
        requiresCustomerConfirmation: true,
      }],
    };

    expect(restoreCommittedHistory([assistantWithCard], welcome)).toEqual([assistantWithCard]);
  });
});
