import type { ChatMessage } from "../../types";

type ChatMessageBubbleProps = {
  message: ChatMessage;
};

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isCustomer = message.role === "user";
  const createdAt = new Date(message.createdAt);

  return (
    <article className={`cmc-chat-message ${isCustomer ? "customer" : "assistant"}`}>
      <div className="cmc-chat-message-meta">
        <span>{isCustomer ? "Bạn" : "CMC AI"}</span>
        <time dateTime={message.createdAt}>
          {Number.isNaN(createdAt.getTime())
            ? "vừa xong"
            : createdAt.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
        </time>
      </div>
      <p>{message.content}</p>
    </article>
  );
}
