import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChatMessageBubble } from "../../components/chatbot/ChatMessageBubble";
import { SuggestedCartActionCard } from "../../components/chatbot/SuggestedCartActionCard";
import "../../components/chatbot/chatbot.css";
import {
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import { chatApi } from "../../services/chatService";
import { getCustomerMenu } from "../../services/menuService";
import type { ChatMessage, MenuItem, SuggestedCartAction } from "../../types";
import { PageShell } from "../PageShell";

type ActionStatus = "pending" | "confirmed" | "dismissed";

const quickPrompts = [
  "Gợi ý món nhẹ cho 2 người",
  "Có món nào hợp ăn trưa không?",
  "Tôi muốn đồ uống thanh mát",
  "Có món hải sản nào không?",
];

const initialMessages: ChatMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Xin chào, mình là trợ lý AI của CMC Restaurant. Mình có thể gợi ý món và tạo thẻ đề xuất, nhưng chỉ thêm vào giỏ khi bạn xác nhận.",
    createdAt: new Date().toISOString(),
  },
];

function getCartTotal() {
  if (typeof window === "undefined") {
    return 0;
  }

  return Object.values(loadMenuCart()).reduce((total, quantity) => total + quantity, 0);
}

function getActionKey(action: SuggestedCartAction) {
  return `${action.menuItemId}:${action.quantity}`;
}

function buildUserMessage(content: string): ChatMessage {
  return {
    id: `user_${Date.now().toString(36)}`,
    role: "user",
    content,
    createdAt: new Date().toISOString(),
  };
}

export function ChatbotPage() {
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [composerValue, setComposerValue] = useState("");
  const [isAssistantThinking, setIsAssistantThinking] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [suggestedActions, setSuggestedActions] = useState<SuggestedCartAction[]>([]);
  const [actionStatuses, setActionStatuses] = useState<Record<string, ActionStatus>>({});
  const [cartTotal, setCartTotal] = useState(getCartTotal);
  const [cartNotice, setCartNotice] = useState("");
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);

  const tableCode = useMemo(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    return loadOrderContext().tableCode;
  }, []);

  useEffect(() => {
    let isMounted = true;

    getCustomerMenu()
      .then((menu) => {
        if (isMounted) {
          setMenuItems(menu.items);
        }
      })
      .catch(() => {
        if (isMounted) {
          setMenuItems([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    chatApi
      .createSession()
      .then((session) => {
        if (isMounted) {
          setChatSessionId(session.chatSessionId);
        }
      })
      .catch(() => {
        if (isMounted) {
          setErrorMessage("Chưa kết nối được trợ lý AI. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function sendMessage(event?: FormEvent<HTMLFormElement>, overrideContent?: string) {
    event?.preventDefault();

    const content = (overrideContent ?? composerValue).trim();

    if (!content || isAssistantThinking || !chatSessionId) {
      return;
    }

    const userMessage = buildUserMessage(content);

    setMessages((current) => [...current, userMessage]);
    setComposerValue("");
    setIsAssistantThinking(true);
    setErrorMessage("");
    setCartNotice("");

    try {
      const response = await chatApi.sendMessage(chatSessionId, {
        content,
        tableCode,
      });

      setMessages((current) => [...current, response.message]);
      setSuggestedActions(response.suggestedCartActions);
      setActionStatuses(
        response.suggestedCartActions.reduce<Record<string, ActionStatus>>((result, action) => {
          result[getActionKey(action)] = "pending";
          return result;
        }, {}),
      );
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: `fallback_${Date.now().toString(36)}`,
          role: "assistant",
          content:
            "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống.",
          createdAt: new Date().toISOString(),
        },
      ]);
      setSuggestedActions([]);
      setErrorMessage("AI không tự tạo đơn và không tự thêm món khi gặp lỗi kết nối.");
    } finally {
      setIsAssistantThinking(false);
    }
  }

  function confirmSuggestedAction(action: SuggestedCartAction) {
    const menuItem = menuItems.find((item) => item.id === action.menuItemId);

    if (!menuItem || !menuItem.isAvailable) {
      setErrorMessage("Món này không còn khả dụng nên không thể thêm vào giỏ.");
      return;
    }

    const currentCart = loadMenuCart();
    const nextQuantity = (currentCart[action.menuItemId] ?? 0) + action.quantity;
    const nextCart = {
      ...currentCart,
      [action.menuItemId]: nextQuantity,
    };

    saveMenuCart(nextCart);
    setCartTotal(Object.values(nextCart).reduce((total, quantity) => total + quantity, 0));
    setCartNotice(`${action.name} đã được thêm vào giỏ sau khi bạn xác nhận.`);
    setActionStatuses((current) => ({
      ...current,
      [getActionKey(action)]: "confirmed",
    }));
  }

  function dismissSuggestedAction(action: SuggestedCartAction) {
    setActionStatuses((current) => ({
      ...current,
      [getActionKey(action)]: "dismissed",
    }));
  }

  return (
    <PageShell
      eyebrow="AI Chat"
      title="Trợ lý gợi ý món CMC"
      description="Chatbot hỗ trợ hỏi đáp menu, tạo gợi ý giỏ hàng và luôn yêu cầu khách xác nhận trước khi thêm món."
      variant="chat"
      stats={[
        {
          label: "Phiên chat",
          value: chatSessionId ? "Sẵn sàng" : "Đang kết nối",
          detail: "Frontend gọi lớp chat API qua backend",
        },
        {
          label: "Giỏ hiện tại",
          value: `${cartTotal} món`,
          detail: "Chỉ thay đổi sau khi khách bấm xác nhận",
        },
        {
          label: "Guardrail",
          value: "Bật",
          detail: "Không tự đặt đơn, không tự thanh toán",
        },
      ]}
    >
      <div className="cmc-chat-layout">
        <section className="cmc-chat-panel" aria-label="Chatbot CMC Restaurant">
          <div className="cmc-chat-session-bar">
            <div>
              <p className="cmc-chat-muted">Luồng an toàn</p>
              <h3>Hỏi món, nhận gợi ý, xác nhận thủ công</h3>
            </div>
            <span className="cmc-chat-muted">
              {tableCode ? `Bàn ${tableCode}` : "Khách online / mang về"}
            </span>
          </div>

          <div className="cmc-chat-transcript" aria-live="polite">
            {messages.map((message) => (
              <ChatMessageBubble key={message.id} message={message} />
            ))}
            {isAssistantThinking ? (
              <div className="cmc-chat-typing" aria-label="Assistant đang phản hồi">
                <span />
                <span />
                <span />
              </div>
            ) : null}
          </div>

          <form className="cmc-chat-composer" onSubmit={(event) => sendMessage(event)}>
            <textarea
              aria-label="Nội dung chat"
              placeholder="Ví dụ: Gợi ý món cho 2 người ăn trưa"
              value={composerValue}
              onChange={(event) => setComposerValue(event.target.value)}
            />
            <div className="cmc-chat-composer-actions">
              <button
                className="cmc-chat-button primary"
                disabled={isAssistantThinking || !chatSessionId}
                type="submit"
              >
                Gửi tin nhắn
              </button>
              <span className="cmc-chat-muted">AI chỉ đề xuất, không tự sửa giỏ hàng.</span>
            </div>
          </form>
        </section>

        <aside className="cmc-chat-side-panel" aria-label="Gợi ý và xác nhận giỏ hàng">
          <div>
            <p className="cmc-chat-muted">Gợi ý nhanh</p>
            <div className="cmc-chat-quick-prompts">
              {quickPrompts.map((prompt) => (
                <button
                  disabled={!chatSessionId || isAssistantThinking}
                  key={prompt}
                  type="button"
                  onClick={() => sendMessage(undefined, prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {cartNotice ? (
            <p className="cmc-chat-notice">
              {cartNotice} <Link to="/cart">Xem giỏ hàng</Link>
            </p>
          ) : null}

          {errorMessage ? <p className="cmc-chat-error">{errorMessage}</p> : null}

          <div className="cmc-suggestion-list">
            {suggestedActions.length > 0 ? (
              suggestedActions.map((action) => (
                <SuggestedCartActionCard
                  action={action}
                  key={getActionKey(action)}
                  status={actionStatuses[getActionKey(action)] ?? "pending"}
                  onConfirm={confirmSuggestedAction}
                  onDismiss={dismissSuggestedAction}
                />
              ))
            ) : (
              <p className="cmc-chat-muted">
                Chưa có gợi ý nào. Hãy gửi câu hỏi để chatbot đề xuất món phù hợp.
              </p>
            )}
          </div>
        </aside>
      </div>
    </PageShell>
  );
}
