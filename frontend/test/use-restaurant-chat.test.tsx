import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRestaurantChat } from "../src/hooks/useRestaurantChat";


const mocks = vi.hoisted(() => ({
  createSession: vi.fn(),
  getHistory: vi.fn(),
  sendMessage: vi.fn(),
}));

vi.mock("../src/components/customer/customerMenuStorage", () => ({
  loadOrderContext: () => ({ tableCode: "T05", sessionId: "table-session-1" }),
}));

vi.mock("../src/services/chatService", () => ({
  chatApi: mocks,
}));

const diagnostics = {
  aiServiceAvailable: true,
  llmProviderAvailable: false,
  model: "gc/gemini-3-flash",
  retrievalMethod: "tfidf",
  fastPath: "price",
  latencyMs: { total: 1.2 },
  retrievedSources: [],
};

describe("useRestaurantChat", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
    mocks.createSession.mockResolvedValue({
      chatSessionId: "chat-1",
      createdAt: "2026-07-10T00:00:00Z",
      reused: false,
    });
  });

  it("creates a table-bound session and stores a grounded assistant turn", async () => {
    mocks.sendMessage.mockResolvedValue({
      message: {
        id: "assistant-1",
        role: "assistant",
        content: "Phở bò tái nạm có giá 75.000 VND.",
        createdAt: "2026-07-10T00:00:02Z",
      },
      suggestedCartActions: [],
      guardrailFlags: [],
      diagnostics,
    });

    const { result } = renderHook(() => useRestaurantChat());
    await waitFor(() => expect(result.current.chatSessionId).toBe("chat-1"));
    expect(mocks.createSession).toHaveBeenCalledWith({
      tableCode: "T05",
      tableSessionId: "table-session-1",
    });
    expect(sessionStorage.getItem("cmc-chat-session:table-session-1")).toBe("chat-1");

    await act(async () => {
      await result.current.send(undefined, "Giá của Phở bò tái nạm bao nhiêu?");
    });

    expect(mocks.sendMessage).toHaveBeenCalledWith("chat-1", {
      content: "Giá của Phở bò tái nạm bao nhiêu?",
    });
    expect(result.current.messages.at(-1)?.content).toContain("75.000 VND");
    expect(result.current.diagnostics?.retrievalMethod).toBe("tfidf");
  });

  it("restores persisted history without creating a duplicate session", async () => {
    sessionStorage.setItem("cmc-chat-session:table-session-1", "chat-existing");
    mocks.getHistory.mockResolvedValue({
      chatSessionId: "chat-existing",
      createdAt: "2026-07-10T00:00:00Z",
      updatedAt: "2026-07-10T00:00:01Z",
      messages: [
        {
          id: "assistant-old",
          role: "assistant",
          content: "Lịch sử đã lưu.",
          createdAt: "2026-07-10T00:00:01Z",
          suggestedCartActions: [],
        },
      ],
    });

    const { result } = renderHook(() => useRestaurantChat());
    await waitFor(() => expect(result.current.chatSessionId).toBe("chat-existing"));

    expect(result.current.messages[0].content).toBe("Lịch sử đã lưu.");
    expect(mocks.createSession).not.toHaveBeenCalled();
  });
});
