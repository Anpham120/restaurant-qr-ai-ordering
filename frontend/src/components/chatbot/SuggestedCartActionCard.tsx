import type { SuggestedCartAction } from "../../types";

type SuggestedCartActionCardProps = {
  action: SuggestedCartAction;
  status: "pending" | "confirmed" | "dismissed";
  imageUrl?: string | null;
  onConfirm: (action: SuggestedCartAction) => void;
  onDismiss: (action: SuggestedCartAction) => void;
};

function formatVnd(value: number) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

export function SuggestedCartActionCard({
  action,
  status,
  imageUrl,
  onConfirm,
  onDismiss,
}: SuggestedCartActionCardProps) {
  return (
    <article className={`cmc-suggestion-card ${status}`}>
      {imageUrl ? (
        <img className="cmc-suggestion-image" alt={action.name} src={imageUrl} loading="lazy" />
      ) : null}
      <div>
        <p className="cmc-suggestion-eyebrow">Gợi ý cần xác nhận</p>
        <h3>{action.name}</h3>
        <p>{action.reason}</p>
        <p className="cmc-suggestion-confirmation">
          AI chỉ đề xuất món này. Giỏ hàng chỉ thay đổi sau khi bạn bấm xác nhận.
        </p>
      </div>
      <dl>
        <div>
          <dt>Giá</dt>
          <dd>{formatVnd(action.price)}</dd>
        </div>
        <div>
          <dt>Số lượng</dt>
          <dd>{action.quantity}</dd>
        </div>
      </dl>
      {status === "pending" ? (
        <div className="cmc-suggestion-actions">
          <button type="button" className="cmc-chat-button primary" onClick={() => onConfirm(action)}>
            Xác nhận thêm vào giỏ
          </button>
          <button type="button" className="cmc-chat-button ghost" onClick={() => onDismiss(action)}>
            Bỏ qua
          </button>
        </div>
      ) : (
        <p className="cmc-suggestion-status">
          {status === "confirmed"
            ? "Đã thêm vào giỏ sau khi bạn xác nhận."
            : "Bạn đã bỏ qua gợi ý này."}
        </p>
      )}
    </article>
  );
}
