import { PageShell } from "./PageShell";

export function ChatPage() {
  return (
    <PageShell
      eyebrow="Chatbot"
      title="AI assistant shell"
      description="Placeholder for chatbot sessions and messages aligned with the chat API contract."
      variant="chat"
      stats={[
        { label: "Session", value: "Draft", detail: "No provider connected" },
        { label: "Endpoint", value: "Chat", detail: "Contract shell only" },
      ]}
    >
      <div className="chat-shell">
        <div className="message assistant">Ask about menu items, allergens, or order help.</div>
        <div className="message customer">Can you suggest something light?</div>
        <div className="message assistant">This is a static preview; AI integration comes later.</div>
      </div>
    </PageShell>
  );
}
