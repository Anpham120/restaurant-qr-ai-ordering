import { useNavigate } from "react-router-dom";
import { formatVnd } from "../menu/MenuItemCard";
import type { MouseEvent } from "react";

type CustomerCartBarProps = {
  itemCount: number;
  totalPrice: number;
  onViewCart?: (e: MouseEvent) => void;
  disabled?: boolean;
};

export function CustomerCartBar({
  itemCount,
  totalPrice,
  onViewCart,
  disabled,
}: CustomerCartBarProps) {
  const navigate = useNavigate();

  if (itemCount === 0) {
    return null;
  }

  function handleClick(e: MouseEvent) {
    if (onViewCart) {
      onViewCart(e);
    }
    if (!e.defaultPrevented) {
      navigate("/cart");
    }
  }

  return (
    <aside className="cmc-cart-bar" aria-label="Tóm tắt giỏ hàng">
      <div className="cmc-cart-bar-info">
        <div className="cmc-cart-bar-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="22" height="22">
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
          <span className="cmc-cart-bar-badge">{itemCount}</span>
        </div>
        <div className="cmc-cart-bar-text">
          <span>{itemCount} món đã chọn</span>
          <strong>{formatVnd(totalPrice)}</strong>
        </div>
      </div>
      <button
        className="cmc-cart-bar-btn"
        onClick={handleClick}
        disabled={disabled}
        type="button"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        Xem giỏ &amp; gửi đơn
      </button>
    </aside>
  );
}
