import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  CART_UPDATED_EVENT,
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
} from "./customerMenuStorage";
import { fetchCustomerMenu } from "../../services/menuService";
import type { MenuCart, MenuItem } from "../../types";
import "./customer-floating-cart.css";

const formatVnd = (v: number) => v.toLocaleString("vi-VN") + "đ";

/**
 * Giỏ hàng nổi toàn cục: mounted ở CustomerLayout nên luôn hiển thị
 * trước màn hình trên mọi trang (thực đơn, chat AI, trang chủ...),
 * trừ trang thanh toán /cart. Mở rộng thành mini-cart chỉnh số lượng
 * tại chỗ, nút "Xem giỏ & gửi đơn" dẫn tới luồng đặt món thật.
 */
export function CustomerFloatingCart() {
  const location = useLocation();
  const navigate = useNavigate();
  const [cart, setCart] = useState<MenuCart>({});
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [orderContext, setOrderContext] = useState(() =>
    typeof window === "undefined" ? {} : loadOrderContext(),
  );
  const [expanded, setExpanded] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const panelRef = useRef<HTMLDivElement | null>(null);
  const dragState = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null);
  const hasLoadedMenu = useRef(false);

  const syncFromStorage = useCallback(() => {
    setCart(loadMenuCart());
    setOrderContext(loadOrderContext());
  }, []);

  useEffect(() => {
    syncFromStorage();
    window.addEventListener(CART_UPDATED_EVENT, syncFromStorage);
    window.addEventListener("storage", syncFromStorage);
    return () => {
      window.removeEventListener(CART_UPDATED_EVENT, syncFromStorage);
      window.removeEventListener("storage", syncFromStorage);
    };
  }, [syncFromStorage]);

  // Đồng bộ lại khi đổi trang (một số trang tự ghi localStorage khi unmount)
  useEffect(() => {
    syncFromStorage();
    setExpanded(false);
  }, [location.pathname, syncFromStorage]);

  const itemCount = useMemo(
    () => Object.values(cart).reduce((sum, q) => sum + q, 0),
    [cart],
  );

  // Chỉ tải chi tiết menu khi thật sự cần hiển thị (giỏ có món)
  useEffect(() => {
    if (itemCount === 0 || hasLoadedMenu.current) return;
    hasLoadedMenu.current = true;
    fetchCustomerMenu()
      .then((menu) => setMenuItems(menu.items))
      .catch(() => {
        hasLoadedMenu.current = false;
      });
  }, [itemCount]);

  const cartItems = useMemo(
    () => menuItems.filter((item) => (cart[item.id] ?? 0) > 0),
    [menuItems, cart],
  );

  const totalPrice = useMemo(
    () => cartItems.reduce((sum, item) => sum + (cart[item.id] ?? 0) * item.price, 0),
    [cartItems, cart],
  );

  // Đóng panel khi bấm ra ngoài
  useEffect(() => {
    if (!expanded) return;
    function onPointerDown(event: PointerEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setExpanded(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setExpanded(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [expanded]);

  const isCheckoutPage = location.pathname.startsWith("/cart");
  if (itemCount === 0 || isCheckoutPage) {
    return null;
  }

  const hasSession = Boolean(
    orderContext.tableCode && orderContext.qrToken && orderContext.sessionId,
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

  function clampDragOffset(x: number, y: number) {
    if (typeof window === "undefined") return { x, y };

    return {
      x: Math.min(0, Math.max(-(window.innerWidth - 96), x)),
      y: Math.min(0, Math.max(-(window.innerHeight - 96), y)),
    };
  }

  function startDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragState.current = {
      startX: event.clientX,
      startY: event.clientY,
      originX: dragOffset.x,
      originY: dragOffset.y,
    };
  }

  function moveDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    if (!dragState.current) return;
    const nextX = dragState.current.originX + event.clientX - dragState.current.startX;
    const nextY = dragState.current.originY + event.clientY - dragState.current.startY;
    setDragOffset(clampDragOffset(nextX, nextY));
  }

  function endDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    dragState.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  return (
    <div
      className="cfc-root"
      ref={panelRef}
      style={{ transform: `translate(${dragOffset.x}px, ${dragOffset.y}px)` }}
    >
      {expanded ? (
        <section className="cfc-panel" aria-label="Giỏ hàng của bạn">
          <header className="cfc-panel-header">
            <div>
              <strong>Giỏ hàng</strong>
              <span>
                {hasSession ? `Bàn ${orderContext.tableCode}` : "Chưa mở phiên bàn"}
              </span>
            </div>
            <button
              className="cfc-drag-handle"
              onPointerDown={startDrag}
              onPointerMove={moveDrag}
              onPointerUp={endDrag}
              onPointerCancel={endDrag}
              type="button"
              aria-label="Di chuyển giỏ hàng"
              title="Giữ và kéo để di chuyển"
            >
              Di chuyển
            </button>
            <button
              className="cfc-close"
              onClick={() => setExpanded(false)}
              type="button"
              aria-label="Thu gọn giỏ hàng"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18" aria-hidden="true">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
          </header>

          <div className="cfc-items">
            {cartItems.length === 0 ? (
              <p className="cfc-loading">Đang tải chi tiết món...</p>
            ) : (
              cartItems.map((item) => (
                <div className="cfc-item" key={item.id}>
                  {item.imageUrl ? <img alt="" src={item.imageUrl} /> : null}
                  <div className="cfc-item-copy">
                    <strong>{item.name}</strong>
                    <span>{formatVnd(item.price)}</span>
                  </div>
                  <div className="cfc-qty">
                    <button
                      onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) - 1)}
                      type="button"
                      aria-label={`Giảm ${item.name}`}
                    >
                      −
                    </button>
                    <span>{cart[item.id]}</span>
                    <button
                      onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) + 1)}
                      type="button"
                      aria-label={`Thêm ${item.name}`}
                    >
                      +
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <footer className="cfc-footer">
            <div className="cfc-total">
              <span>Tạm tính ({itemCount} món)</span>
              <strong>{formatVnd(totalPrice)}</strong>
            </div>
            {!hasSession ? (
              <p className="cfc-session-hint">
                Quét QR tại bàn để mở phiên trước khi gửi đơn cho bếp.
              </p>
            ) : null}
            <button
              className="cfc-checkout-btn"
              onClick={() => {
                setExpanded(false);
                navigate("/cart");
              }}
              type="button"
            >
              Xem giỏ &amp; gửi đơn
            </button>
          </footer>
        </section>
      ) : null}

      <button
        className={`cfc-fab${expanded ? " is-open" : ""}`}
        onClick={() => setExpanded((v) => !v)}
        type="button"
        aria-expanded={expanded}
        aria-label={`Giỏ hàng: ${itemCount} món, ${formatVnd(totalPrice)}`}
      >
        <span className="cfc-fab-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="22" height="22" aria-hidden="true">
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
          <span className="cfc-badge">{itemCount}</span>
        </span>
        <span className="cfc-fab-total">{formatVnd(totalPrice)}</span>
      </button>
    </div>
  );
}
