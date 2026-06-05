import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  loadMenuCart,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import { formatVnd } from "../../components/menu/MenuItemCard";
import { menuItems } from "../../mocks/menuItems";
import type { MenuCart } from "../../types";

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

export function CustomerCartPage() {
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const selectedItems = useMemo(
    () => menuItems.filter((item) => (cart[item.id] ?? 0) > 0),
    [cart],
  );
  const totalPrice = selectedItems.reduce(
    (total, item) => total + (cart[item.id] ?? 0) * item.price,
    0,
  );

  function updateQuantity(itemId: string, nextQuantity: number) {
    const nextCart = { ...cart };
    if (nextQuantity <= 0) {
      delete nextCart[itemId];
    } else {
      nextCart[itemId] = nextQuantity;
    }

    setCart(nextCart);
    saveMenuCart(nextCart);
  }

  return (
    <section className="cmc-customer-page cmc-cart-page">
      <header className="cmc-hero">
        <div>
          <p className="cmc-kicker">Giỏ hàng</p>
          <h2>
            Kiểm tra món trước khi <span>gửi bếp</span>
          </h2>
          <p>
            Đây là giỏ hàng mock để kiểm tra giao diện. Chưa có API đặt món thật
            trong phạm vi issue #5.
          </p>
          <div className="cmc-hero-actions">
            <Link className="cmc-secondary-link" to="/menu">
              Thêm món khác
            </Link>
          </div>
        </div>
      </header>

      <div className="cmc-cart-panel" aria-label="Cart details">
        {selectedItems.length === 0 ? (
          <div className="cmc-empty-state">
            Giỏ hàng đang trống. Quay lại thực đơn để chọn món.
          </div>
        ) : (
          selectedItems.map((item) => (
            <div className="cmc-cart-row" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <span>{formatVnd(item.price)}</span>
              </div>
              <div className="cmc-stepper">
                <button
                  onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) - 1)}
                  type="button"
                >
                  -
                </button>
                <span>{cart[item.id]}</span>
                <button
                  onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) + 1)}
                  type="button"
                >
                  +
                </button>
              </div>
            </div>
          ))
        )}
        <div className="cmc-cart-total">
          <span>Tổng cộng</span>
          <strong>{formatVnd(totalPrice)}</strong>
        </div>
        <button className="cmc-add-button" disabled={selectedItems.length === 0} type="button">
          Gửi đơn mock
        </button>
      </div>
    </section>
  );
}

