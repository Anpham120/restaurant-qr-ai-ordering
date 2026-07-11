import { useNavigate } from "react-router-dom";
import { formatVnd } from "../menu/MenuItemCard";
import type { MouseEvent } from "react";
import { Eye, ShoppingCart } from "lucide-react";

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
          <ShoppingCart aria-hidden="true" size={22} />
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
        <Eye aria-hidden="true" size={18} />
        Xem giỏ &amp; gửi đơn
      </button>
    </aside>
  );
}
