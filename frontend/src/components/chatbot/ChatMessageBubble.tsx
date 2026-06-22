import type { ChatMessage } from "../../types";

type ChatMessageBubbleProps = {
  message: ChatMessage;
};

function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let listBuffer: string[] = [];
  let listType: "ul" | "ol" | null = null;

  function flushList() {
    if (listBuffer.length === 0 || !listType) {
      return;
    }

    const Tag = listType;
    elements.push(
      <Tag key={`list-${elements.length}`}>
        {listBuffer.map((item, i) => (
          <li key={i}>{inlineFormat(item)}</li>
        ))}
      </Tag>,
    );
    listBuffer = [];
    listType = null;
  }

  function inlineFormat(line: string): React.ReactNode {
    const parts: React.ReactNode[] = [];
    let remaining = line;
    let keyIdx = 0;

    while (remaining.length > 0) {
      const boldMatch = remaining.match(/\*\*(.+?)\*\*/);

      if (!boldMatch || boldMatch.index === undefined) {
        parts.push(remaining);
        break;
      }

      if (boldMatch.index > 0) {
        parts.push(remaining.slice(0, boldMatch.index));
      }

      parts.push(<strong key={keyIdx++}>{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
    }

    return parts.length === 1 ? parts[0] : parts;
  }

  for (const line of lines) {
    const trimmed = line.trim();

    const ulMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (ulMatch) {
      if (listType !== "ul") {
        flushList();
      }

      listType = "ul";
      listBuffer.push(ulMatch[1]);
      continue;
    }

    const olMatch = trimmed.match(/^\d+[.)]\s+(.+)/);
    if (olMatch) {
      if (listType !== "ol") {
        flushList();
      }

      listType = "ol";
      listBuffer.push(olMatch[1]);
      continue;
    }

    flushList();

    if (trimmed === "") {
      elements.push(<br key={`br-${elements.length}`} />);
    } else {
      elements.push(<p key={`p-${elements.length}`}>{inlineFormat(trimmed)}</p>);
    }
  }

  flushList();
  return elements;
}

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
      <div className="cmc-chat-message-body">
        {isCustomer ? <p>{message.content}</p> : renderMarkdown(message.content)}
      </div>
    </article>
  );
}
