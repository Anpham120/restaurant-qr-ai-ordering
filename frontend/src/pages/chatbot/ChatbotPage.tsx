import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChatMessageBubble } from "../../components/chatbot/ChatMessageBubble";
import { SuggestedCartActionCard } from "../../components/chatbot/SuggestedCartActionCard";
import "../../components/chatbot/chatbot.css";
import "../../components/chatbot/chatbot-vian-theme.css";
import { loadMenuCart, saveMenuCart } from "../../components/customer/customerMenuStorage";
import { useRestaurantChat } from "../../hooks/useRestaurantChat";
import { fetchCustomerMenu } from "../../services/menuService";
import type { CustomerMenuResponse } from "../../services/menuService";
import type { SuggestedCartAction } from "../../types";


type ActionStatus = "pending" | "confirmed" | "dismissed";

const quickPrompts = [
  "Gợi ý món nhẹ cho 2 người",
  "Tôi muốn món chay dạng nước",
  "Giá của Phở bò tái nạm bao nhiêu?",
  "Nhà hàng thanh toán bằng cách nào?",
];

function actionKey(action: SuggestedCartAction) {
  return `${action.menuItemId}:${action.quantity}`;
}

export function ChatbotPage() {
  const chat = useRestaurantChat();
  const [menu, setMenu] = useState<CustomerMenuResponse>({ categories: [], items: [] });
  const [statuses, setStatuses] = useState<Record<string, ActionStatus>>({});
  const [notice, setNotice] = useState("");
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchCustomerMenu().then(setMenu).catch(() => {});
  }, []);

  useEffect(() => {
    setStatuses(Object.fromEntries(chat.suggestions.map((action) => [actionKey(action), "pending"])));
  }, [chat.suggestions]);

  useEffect(() => {
    if (transcriptRef.current) transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [chat.messages, chat.suggestions, chat.thinking]);

  function confirm(action: SuggestedCartAction) {
    if (!chat.orderContext.sessionId || !chat.orderContext.tableCode) {
      chat.setError("Bạn cần quét QR tại bàn trước khi thêm gợi ý vào giỏ.");
      return;
    }
    const item = menu.items.find((value) => value.id === action.menuItemId && value.isAvailable);
    if (!item) {
      chat.setError("Món này không còn trong menu khả dụng.");
      return;
    }
    const cart = loadMenuCart();
    saveMenuCart({ ...cart, [item.id]: (cart[item.id] ?? 0) + action.quantity });
    setStatuses((current) => ({ ...current, [actionKey(action)]: "confirmed" }));
    setNotice(`${item.name} đã được thêm vào giỏ sau khi bạn xác nhận.`);
  }

  return (
    <div className="page-shell page-shell-chat">
      <div className="cmc-chat-layout">
        <section className="cmc-chat-panel" aria-label="AI tư vấn CMC Restaurant">
          <div className="cmc-chat-session-bar">
            <div>
              <h3>AI tư vấn thực đơn</h3>
              <p className="cmc-chat-muted">Tra cứu trực tiếp menu 91 món · AI không tự đặt hàng</p>
            </div>
            {chat.orderContext.tableCode ? <span className="cmc-chat-muted">Bàn {chat.orderContext.tableCode}</span> : null}
          </div>

          <div className="cmc-chat-transcript" ref={transcriptRef} aria-live="polite">
            {chat.messages.map((message) => <ChatMessageBubble key={message.id} message={message} />)}
            {chat.suggestions.length > 0 ? (
              <div className="cmc-chat-suggestions-inline" aria-label="Gợi ý món cần xác nhận">
                {chat.suggestions.map((action) => {
                  const item = menu.items.find((value) => value.id === action.menuItemId);
                  return (
                    <SuggestedCartActionCard
                      action={{ ...action, name: item?.name ?? action.name, price: item?.price ?? action.price }}
                      key={actionKey(action)}
                      status={statuses[actionKey(action)] ?? "pending"}
                      imageUrl={item?.imageUrl}
                      isAvailable={Boolean(item?.isAvailable)}
                      onConfirm={confirm}
                      onDismiss={(value) => setStatuses((current) => ({ ...current, [actionKey(value)]: "dismissed" }))}
                    />
                  );
                })}
              </div>
            ) : null}
            {chat.thinking ? <div className="cmc-chat-typing" aria-label="Đang phản hồi"><span /><span /><span /></div> : null}
          </div>

          <form className="cmc-chat-composer" onSubmit={(event) => chat.send(event)}>
            <textarea
              aria-label="Nhập tin nhắn"
              placeholder="Hỏi về món, giá, khẩu vị hoặc chính sách..."
              value={chat.input}
              maxLength={1000}
              onChange={(event) => chat.setInput(event.target.value)}
            />
            <div className="cmc-chat-composer-actions">
              <button className="cmc-chat-button primary" disabled={!chat.ready || !chat.chatSessionId || chat.thinking || !chat.input.trim()} type="submit">Gửi</button>
            </div>
          </form>
        </section>

        <aside className="cmc-chat-side-panel" aria-label="Gợi ý nhanh">
          <p className="cmc-chat-muted">Gợi ý nhanh</p>
          <div className="cmc-chat-quick-prompts">
            {quickPrompts.map((prompt) => <button key={prompt} type="button" disabled={!chat.chatSessionId || chat.thinking} onClick={() => chat.send(undefined, prompt)}>{prompt}</button>)}
          </div>
          {chat.diagnostics ? (
            <details className="cmc-chat-diagnostics">
              <summary>Thông tin truy xuất</summary>
              <p>Phương pháp: {chat.diagnostics.retrievalMethod}</p>
              <p>Đường nhanh: {chat.diagnostics.fastPath ?? "LLM"}</p>
              <p>Độ trễ AI: {chat.diagnostics.latencyMs.total?.toFixed(1) ?? "–"} ms</p>
            </details>
          ) : null}
          {notice ? <p className="cmc-chat-notice">{notice} <Link to="/cart">Xem giỏ hàng</Link></p> : null}
          {chat.error ? <p className="cmc-chat-error">{chat.error}</p> : null}
        </aside>
      </div>
    </div>
  );
}
