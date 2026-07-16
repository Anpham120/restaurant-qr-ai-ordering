import { useState } from "react";
import { useI18n } from "@cmc/i18n";
import { localizeMenuItemName } from "@cmc/i18n/menu";
import type { SuggestedCartAction } from "../../types";

type SuggestedCartActionCardProps = {
  action: SuggestedCartAction;
  status: "pending" | "confirmed" | "dismissed";
  imageUrl?: string | null;
  isAvailable?: boolean;
  onConfirm: (action: SuggestedCartAction) => void;
  onDismiss: (action: SuggestedCartAction) => void;
};

export function SuggestedCartActionCard({
  action,
  status,
  imageUrl,
  isAvailable = true,
  onConfirm,
  onDismiss,
}: SuggestedCartActionCardProps) {
  const { formatMoney, locale, t } = useI18n();
  const [quantity, setQuantity] = useState(action.quantity);
  const displayName = localizeMenuItemName(action.menuItemId, action.name, locale);

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
        <img className="cmc-suggestion-image" alt={displayName} src={imageUrl} loading="lazy" />
      ) : null}
      <div>
        <p className="cmc-suggestion-eyebrow">
          {isAvailable ? t("Gợi ý cần xác nhận") : t("Tạm hết hàng")}
        </p>
        <h3>{displayName}</h3>
        <p>{action.reason}</p>
        {isAvailable ? (
          <p className="cmc-suggestion-confirmation">
            {t("AI chỉ đề xuất món này. Giỏ hàng chỉ thay đổi sau khi bạn bấm xác nhận.")}
          </p>
        ) : (
          <p className="cmc-suggestion-unavailable">
            {t("Món này tạm hết. Không thể thêm vào giỏ hàng.")}
          </p>
        )}
      </div>
      <dl>
        <div>
          <dt>{t("Giá")}</dt>
          <dd data-money>{formatMoney(action.price)}</dd>
        </div>
        <div>
          <dt>{t("Tổng")}</dt>
          <dd data-money>{formatMoney(action.price * quantity)}</dd>
        </div>
      </dl>
      {status === "pending" ? (
        <div className="cmc-suggestion-actions">
          {isAvailable ? (
            <>
              <div className="cmc-suggestion-stepper">
                <button type="button" onClick={decrement} disabled={quantity <= 1}>-</button>
                <span>{quantity}</span>
                <button type="button" onClick={increment}>+</button>
              </div>
              <button type="button" className="cmc-chat-button primary" onClick={handleConfirm}>
                {t("Thêm vào giỏ")}
              </button>
              <button type="button" className="cmc-chat-button ghost" onClick={() => onDismiss(action)}>
                {t("Bỏ qua")}
              </button>
            </>
          ) : (
            <button type="button" className="cmc-chat-button ghost" onClick={() => onDismiss(action)}>
              {t("Bỏ qua")}
            </button>
          )}
        </div>
      ) : (
        <p className="cmc-suggestion-status">
          {status === "confirmed"
            ? t("Đã thêm {count} phần vào giỏ.", { count: quantity })
            : t("Bạn đã bỏ qua gợi ý này.")}
        </p>
      )}
    </article>
  );
}
