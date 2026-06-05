import { PageShell } from "./PageShell";

export function ChatPage() {
  return (
    <PageShell
      eyebrow="AI Chat"
      title="Trợ lý gọi món CMC"
      description="Khung hỏi đáp gợi ý món ăn, khẩu vị và hỗ trợ đơn hàng theo nhận diện CMC."
      variant="chat"
      stats={[
        { label: "Phiên chat", value: "Mock", detail: "Chưa nối provider" },
        { label: "Ngữ cảnh", value: "Menu", detail: "Sẵn sàng nối API chat" },
      ]}
    >
      <div className="chat-shell">
        <div className="message assistant">Bạn muốn món nhẹ, món no hay đồ uống mát?</div>
        <div className="message customer">Gợi ý cho tôi món thanh nhẹ.</div>
        <div className="message assistant">Gỏi cuốn tôm thịt và trà đào cam sả là cặp gợi ý hợp lý.</div>
      </div>
    </PageShell>
  );
}
