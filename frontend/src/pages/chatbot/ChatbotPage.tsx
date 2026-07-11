import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChatMessageBubble } from "../../components/chatbot/ChatMessageBubble";
import { SuggestedCartActionCard } from "../../components/chatbot/SuggestedCartActionCard";
import "../../components/chatbot/chatbot.css";
import "../../components/chatbot/chatbot-vian-theme.css";
import {
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import { chatApi } from "../../services/chatService";
import { fetchCustomerMenu } from "../../services/menuService";
import type { CustomerMenuResponse } from "../../services/menuService";
import type { ChatMessage, SuggestedCartAction } from "../../types";


type ActionStatus = "pending" | "confirmed" | "dismissed";

const quickPrompts = [
  "Gợi ý món nhẹ cho 2 người",
  "Có món nào hợp ăn trưa không?",
  "Tôi muốn đồ uống thanh mát",
  "Có pizza hải sản không?",
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
  const [chatAccessToken, setChatAccessToken] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [suggestedActions, setSuggestedActions] = useState<SuggestedCartAction[]>([]);
  const [actionStatuses, setActionStatuses] = useState<Record<string, ActionStatus>>({});

  const [cartNotice, setCartNotice] = useState("");
  const [menuData, setMenuData] = useState<CustomerMenuResponse>({ categories: [], items: [] });

  const orderContext = useMemo<ReturnType<typeof loadOrderContext>>(() => {
    if (typeof window === "undefined") {
      return {};
    }

    return loadOrderContext();
  }, []);
  const tableCode = orderContext.tableCode;
  const hasTableSession = Boolean(
    orderContext.tableCode && orderContext.sessionId && orderContext.sessionToken,
  );

  useEffect(() => {
    let isMounted = true;

    chatApi
      .createSession({
        tableCode: orderContext.tableCode,
        tableSessionId: orderContext.sessionId,
      })
      .then((session) => {
        if (isMounted) {
          setChatSessionId(session.chatSessionId);
          setChatAccessToken(session.accessToken);
          setMessages(session.messages.length > 0 ? session.messages : initialMessages);
        }
      })
      .catch(() => {
        if (isMounted) {
          setErrorMessage("Không tạo được phiên chat. Vui lòng thử lại sau.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [orderContext.sessionId, orderContext.tableCode]);

  useEffect(() => {
    fetchCustomerMenu().then(setMenuData).catch(() => {});
  }, []);

  async function sendMessage(event?: FormEvent<HTMLFormElement>, overrideContent?: string) {
    event?.preventDefault();

    const content = (overrideContent ?? composerValue).trim();

    if (!content || isAssistantThinking) {
      return;
    }

    if (!chatSessionId || !chatAccessToken) {
      setErrorMessage("Phiên chat chưa sẵn sàng. Vui lòng thử lại sau.");
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
      }, chatAccessToken);

      setMessages((current) => [...current, response.message]);
      setSuggestedActions(response.suggestedCartActions);
      setActionStatuses(
        response.suggestedCartActions.reduce<Record<string, ActionStatus>>((result, action) => {
          result[getActionKey(action)] = "pending";
          return result;
        }, {}),
      );
    } catch {
      setSuggestedActions([]);
      setErrorMessage("Trợ lý AI chưa phản hồi được. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp.");
    } finally {
      setIsAssistantThinking(false);
    }
  }

  function confirmSuggestedAction(action: SuggestedCartAction) {
    if (!hasTableSession) {
      setCartNotice("");
      setErrorMessage("Bạn cần quét QR tại bàn để mở phiên bàn trước khi thêm gợi ý AI vào giỏ.");
      return;
    }

    const menuItem = menuData.items.find((item) => item.id === action.menuItemId);

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
    <div className="page-shell page-shell-chat">
      <div className="cmc-chat-layout">
        <section className="cmc-chat-panel" aria-label="AI Tư vấn CMC Restaurant">
          <div className="cmc-chat-session-bar">
            <div>
              <h3>AI Tư vấn thực đơn</h3>
              <p className="cmc-chat-muted">Hỏi bất cứ điều gì về thực đơn, AI sẽ gợi ý cho bạn</p>
            </div>
            {tableCode ? (
              <span className="cmc-chat-muted">Bàn {tableCode}</span>
            ) : null}
          </div>

          <div className="cmc-chat-transcript" aria-live="polite">
            {messages.map((message) => (
              <ChatMessageBubble key={message.id} message={message} />
            ))}
            {suggestedActions.length > 0 ? (
              <div className="cmc-chat-suggestions-inline" aria-label="Gợi ý món">
                {suggestedActions.map((action) => (
                  <SuggestedCartActionCard
                    action={action}
                    key={getActionKey(action)}
                    status={actionStatuses[getActionKey(action)] ?? "pending"}
                    imageUrl={
                      menuData.items.find((item) => item.id === action.menuItemId)?.imageUrl ?? null
                    }
                    isAvailable={
                      menuData.items.find((item) => item.id === action.menuItemId)?.isAvailable ?? true
                    }
                    onConfirm={confirmSuggestedAction}
                    onDismiss={dismissSuggestedAction}
                  />
                ))}
              </div>
            ) : null}
            {isAssistantThinking ? (
              <div className="cmc-chat-typing" aria-label="Đang phản hồi">
                <span />
                <span />
                <span />
              </div>
            ) : null}
          </div>

          <form className="cmc-chat-composer" onSubmit={(event) => sendMessage(event)}>
            <textarea
              aria-label="Nhập tin nhắn"
              placeholder="Hỏi về thực đơn, gợi ý món..."
              value={composerValue}
              onChange={(event) => setComposerValue(event.target.value)}
            />
            <div className="cmc-chat-composer-actions">
              <button className="cmc-chat-button primary" disabled={isAssistantThinking} type="submit">
                Gửi
              </button>
            </div>
          </form>
        </section>

        <aside className="cmc-chat-side-panel" aria-label="Gợi ý nhanh">
          <div>
            <p className="cmc-chat-muted">Gợi ý nhanh</p>
            <div className="cmc-chat-quick-prompts">
              {quickPrompts.map((prompt) => (
                <button key={prompt} type="button" onClick={() => sendMessage(undefined, prompt)}>
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
        </aside>
      </div>
    </div>
  );
}
