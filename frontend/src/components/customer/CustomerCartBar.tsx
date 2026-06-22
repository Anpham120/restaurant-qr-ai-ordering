import { formatVnd } from "../menu/MenuItemCard";

type CustomerCartBarProps = {
  itemCount: number;
  totalPrice: number;
};

export function CustomerCartBar({ itemCount, totalPrice }: CustomerCartBarProps) {
  if (itemCount === 0) {
    return null;
  }

  return (
    <aside className="cmc-cart-bar" aria-label="Tóm tắt giỏ hàng">
      <div>
        <span>{itemCount} món trong giỏ</span>
        <strong>{formatVnd(totalPrice)}</strong>
      </div>
      <a href="/cart">Xem giỏ hàng</a>
    </aside>
  );
}
