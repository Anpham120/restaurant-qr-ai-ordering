import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { loadOrderContext } from "../components/customer/customerMenuStorage";
import { chatApi } from "../services/chatService";
import type { ChatDiagnostics, ChatMessage, SuggestedCartAction } from "../types";


const welcomeMessage: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content: "Xin chào! Mình có thể tra cứu 91 món và chính sách hiện tại. Mình chỉ đề xuất; bạn luôn là người xác nhận thao tác.",
  createdAt: new Date(0).toISOString(),
};


export function useRestaurantChat() {
  const orderContext = useMemo(() => loadOrderContext(), []);
  const storageKey = `cmc-chat-session:${orderContext.sessionId ?? "anonymous"}`;
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState<SuggestedCartAction[]>([]);
  const [diagnostics, setDiagnostics] = useState<ChatDiagnostics | null>(null);

  useEffect(() => {
    let active = true;
    async function initialize() {
      const stored = typeof window === "undefined" ? null : sessionStorage.getItem(storageKey);
      if (stored) {
        try {
          const history = await chatApi.getHistory(stored);
          if (!active) return;
          setChatSessionId(stored);
          setMessages(history.messages.length ? history.messages : [welcomeMessage]);
          const latest = [...history.messages].reverse().find((message) => message.role === "assistant");
          setSuggestions(latest?.suggestedCartActions ?? []);
          setReady(true);
          return;
        } catch {
          sessionStorage.removeItem(storageKey);
        }
      }

      try {
        const session = await chatApi.createSession({
          tableCode: orderContext.tableCode,
          tableSessionId: orderContext.sessionId,
        });
        if (!active) return;
        sessionStorage.setItem(storageKey, session.chatSessionId);
        setChatSessionId(session.chatSessionId);
        if (session.reused) {
          const history = await chatApi.getHistory(session.chatSessionId);
          if (!active) return;
          setMessages(history.messages.length ? history.messages : [welcomeMessage]);
          const latest = [...history.messages].reverse().find((message) => message.role === "assistant");
          setSuggestions(latest?.suggestedCartActions ?? []);
        }
      } catch {
        if (active) setError("Không thể mở phiên chat. Vui lòng thử lại.");
      } finally {
        if (active) setReady(true);
      }
    }
    initialize();
    return () => {
      active = false;
    };
  }, [orderContext.sessionId, orderContext.tableCode, storageKey]);

  const send = useCallback(async (event?: FormEvent, override?: string) => {
    event?.preventDefault();
    const content = (override ?? input).trim();
    if (!content || thinking || !chatSessionId) return;
    const optimistic: ChatMessage = {
      id: `local_${Date.now()}`,
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    };
    setMessages((current) => [...current, optimistic]);
    setInput("");
    setThinking(true);
    setError("");
    setSuggestions([]);
    try {
      const response = await chatApi.sendMessage(chatSessionId, { content });
      setMessages((current) => [...current, { ...response.message, suggestedCartActions: response.suggestedCartActions }]);
      setSuggestions(response.suggestedCartActions);
      setDiagnostics(response.diagnostics);
    } catch {
      setError("Trợ lý chưa phản hồi được. Bạn vẫn có thể xem menu và gọi món trực tiếp.");
    } finally {
      setThinking(false);
    }
  }, [chatSessionId, input, thinking]);

  return {
    chatSessionId,
    messages,
    input,
    setInput,
    thinking,
    ready,
    error,
    setError,
    suggestions,
    setSuggestions,
    diagnostics,
    send,
    orderContext,
  };
}
