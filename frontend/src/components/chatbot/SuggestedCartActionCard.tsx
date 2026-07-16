import { useState } from "react";
import type { SuggestedCartAction } from "../../types";

type SuggestedCartActionCardProps = {
  action: SuggestedCartAction;
  status: "pending" | "confirmed" | "dismissed";
  imageUrl?: string | null;
  isAvailable?: boolean;
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
  isAvailable = true,
  onConfirm,
  onDismiss,
}: SuggestedCartActionCardProps) {
  const [quantity, setQuantity] = useState(action.quantity);

  function increment() {
    setQuantity((q) => q + 1);
  }

  function decrement() {
    setQuantity((q) => (q > 1 ? q - 1 : 1));
  }

  function handleConfirm() {
    onConfirm({ ...action, quantity });
  }

  return (
    <article className={`cmc-suggestion-card ${status}${isAvailable ? "" : " unavailable"}`}>
      {imageUrl ? (
        <img className="cmc-suggestion-image" alt={action.name} src={imageUrl} loading="lazy" />
      ) : null}
      <div>
        <p className="cmc-suggestion-eyebrow">
          {isAvailable ? "Gợi ý cần xác nhận" : "Tạm hết hàng"}
        </p>
        <h3>{action.name}</h3>
        <p>{action.reason}</p>
        {isAvailable ? (
          <p className="cmc-suggestion-confirmation">
            AI chỉ đề xuất món này. Giỏ hàng chỉ thay đổi sau khi bạn bấm xác nhận.
          </p>
        ) : (
          <p className="cmc-suggestion-unavailable">
            Món này tạm hết. Không thể thêm vào giỏ hàng.
          </p>
        )}
      </div>
      <dl>
        <div>
          <dt>Giá</dt>
          <dd>{formatVnd(action.price)}</dd>
        </div>
        <div>
          <dt>Tổng</dt>
          <dd>{formatVnd(action.price * quantity)}</dd>
        </div>
      </dl>
      {status === "pending" ? (
        <div className="cmc-suggestion-actions">
          {isAvailable ? (
            <>
              <div className="cmc-suggestion-stepper">
                <button type="button" onClick={decrement} disabled={quantity <= 1}>−</button>
                <span>{quantity}</span>
                <button type="button" onClick={increment}>+</button>
              </div>
              <button type="button" className="cmc-chat-button primary" onClick={handleConfirm}>
                Thêm vào giỏ
              </button>
              <button type="button" className="cmc-chat-button ghost" onClick={() => onDismiss(action)}>
                Bỏ qua
              </button>
            </>
          ) : (
            <button type="button" className="cmc-chat-button ghost" onClick={() => onDismiss(action)}>
              Bỏ qua
            </button>
          )}
        </div>
      ) : (
        <p className="cmc-suggestion-status">
          {status === "confirmed"
            ? `Đã thêm ${quantity} phần vào giỏ.`
            : "Bạn đã bỏ qua gợi ý này."}
        </p>
      )}
    </article>
  );
}
