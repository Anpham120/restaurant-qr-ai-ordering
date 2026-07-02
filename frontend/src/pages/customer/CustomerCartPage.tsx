import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  clearMenuCart,
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import { formatVnd } from "../../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../../services/menuService";
import { createOrder, generateVietQrPayment } from "../../services/orderService";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  MenuCart,
  MenuItem,
  PaymentMethod,
  VietQrPaymentResponse,
} from "../../types";

const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function getInitialOrderContext() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadOrderContext();
}

function getCartItems(cart: MenuCart, items: MenuItem[]) {
  return items.filter((item) => (cart[item.id] ?? 0) > 0);
}

function buildOrderPayload(
  cart: MenuCart,
  selectedItems: MenuItem[],
  paymentMethod: PaymentMethod,
  context: ReturnType<typeof getInitialOrderContext>,
): CreateOrderRequest {
  return {
    orderType: "DineIn",
    tableCode: context.tableCode!,
    qrToken: context.qrToken!,
    tableSessionId: context.sessionId!,
    paymentMethod,
    items: selectedItems.map((item) => ({
      menuItemId: item.id,
      quantity: cart[item.id] ?? 0,
    })),
  };
}

export function CustomerCartPage() {
  const [customerMenu, setCustomerMenu] = useState(initialMenu);
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [orderContext] = useState(getInitialOrderContext);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("COD");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successOrder, setSuccessOrder] = useState<CreateOrderResponse | null>(null);
  const [vietQrPayment, setVietQrPayment] = useState<VietQrPaymentResponse | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchCustomerMenu()
      .then((menu) => {
        if (isMounted) {
          setCustomerMenu(menu);
        }
      })
      .catch(() => {
        if (isMounted) {
          setErrorMessage("Không tải được thực đơn từ hệ thống.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const selectedItems = useMemo(
    () => getCartItems(cart, customerMenu.items),
    [cart, customerMenu.items],
  );
  const unavailableItems = selectedItems.filter((item) => !item.isAvailable);
  const totalPrice = selectedItems.reduce(
    (total, item) => total + (cart[item.id] ?? 0) * item.price,
    0,
  );
  const hasActiveSession = Boolean(
    orderContext.tableCode && orderContext.qrToken && orderContext.sessionId,
  );
  const tableMenuPath =
    orderContext.tableCode && orderContext.qrToken
      ? `/table/${orderContext.tableCode}?qr=${encodeURIComponent(orderContext.qrToken)}`
      : "/";
  const canSubmit =
    hasActiveSession &&
    selectedItems.length > 0 &&
    unavailableItems.length === 0 &&
    !isSubmitting;

  function updateQuantity(itemId: string, nextQuantity: number) {
    const nextCart = { ...cart };
    if (nextQuantity <= 0) {
      delete nextCart[itemId];
    } else {
      nextCart[itemId] = nextQuantity;
    }

    setCart(nextCart);
    saveMenuCart(nextCart);
    setSuccessOrder(null);
    setVietQrPayment(null);
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setSuccessOrder(null);
    setVietQrPayment(null);

    if (!hasActiveSession) {
      setErrorMessage("Phiên bàn không hợp lệ. Vui lòng quét lại QR tại bàn để gọi món.");
      return;
    }

    if (!canSubmit) {
      setErrorMessage("Vui lòng kiểm tra giỏ hàng trước khi gửi đơn.");
      return;
    }

    const payload = buildOrderPayload(cart, selectedItems, paymentMethod, orderContext);
    setIsSubmitting(true);

    try {
      const response = await createOrder(payload);
      setSuccessOrder(response);
      if (payload.paymentMethod === "VietQR") {
        setVietQrPayment(await generateVietQrPayment(response.orderCode));
      }
      setCart({});
      clearMenuCart();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Không thể gửi đơn lúc này.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="cmc-customer-page cmc-cart-page">
      <header className="cmc-hero cmc-checkout-hero">
        <div>
          <p className="cmc-kicker">Giỏ hàng tại bàn</p>
          <h2>
            Kiểm tra món và <span>gửi đơn cho bếp</span>
          </h2>
          <p>
            Đơn chỉ được tạo từ phiên QR đang mở tại bàn. Bếp và nhân viên sẽ nhận đúng mã bàn sau khi khách xác nhận.
          </p>
          <div className="cmc-hero-actions">
            <Link className="cmc-secondary-link" to={tableMenuPath}>
              Thêm món khác
            </Link>
            {orderContext.tableCode ? (
              <span className="cmc-table-badge">Bàn {orderContext.tableCode}</span>
            ) : null}
          </div>
        </div>
      </header>

      {!hasActiveSession ? (
        <div className="cmc-empty-state" role="alert">
          Vui lòng quét QR tại bàn để mở phiên gọi món trước khi thanh toán.
        </div>
      ) : null}

      <div className="cmc-checkout-layout">
        <div className="cmc-cart-panel" aria-label="Chi tiết giỏ hàng">
          <div className="cmc-section-title">
            <h3>Món đã chọn</h3>
            <span>{selectedItems.length} món</span>
          </div>

          {selectedItems.length === 0 ? (
            <div className="cmc-empty-state">Giỏ hàng đang trống.</div>
          ) : (
            <div className="cmc-cart-list">
              {selectedItems.map((item) => (
                <div className={item.isAvailable ? "cmc-cart-row" : "cmc-cart-row muted"} key={item.id}>
                  <img alt={item.name} src={item.imageUrl} />
                  <div className="cmc-cart-item-copy">
                    <strong>{item.name}</strong>
                    <span>
                      {formatVnd(item.price)} / {item.categoryName}
                    </span>
                    {!item.isAvailable ? <em>Tạm hết, không thể đặt món này</em> : null}
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
                      disabled={!item.isAvailable}
                      onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) + 1)}
                      type="button"
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="cmc-cart-total">
            <span>Tổng cộng</span>
            <strong>{formatVnd(totalPrice)}</strong>
          </div>

          {unavailableItems.length > 0 ? (
            <p className="cmc-inline-error">
              Có {unavailableItems.length} món tạm hết. Vui lòng bỏ món đó khỏi giỏ trước khi đặt.
            </p>
          ) : null}
        </div>

        <form className="cmc-checkout-panel" onSubmit={submitOrder}>
          <div className="cmc-section-title">
            <h3>Xác nhận gọi món</h3>
            <span>Ăn tại bàn</span>
          </div>

          <div className="cmc-checkout-note">
            <strong>Bàn {orderContext.tableCode ?? "--"}</strong>
            <span>Phiên QR: {orderContext.sessionId ? "đang hoạt động" : "chưa có"}</span>
          </div>

          <div className="cmc-checkout-note">
            <strong>Phương thức thanh toán</strong>
            <div className="cmc-order-type-tabs" role="tablist" aria-label="Phương thức thanh toán">
              {(["COD", "VietQR"] as PaymentMethod[]).map((method) => (
                <button
                  aria-selected={paymentMethod === method}
                  className={paymentMethod === method ? "active" : ""}
                  key={method}
                  onClick={() => setPaymentMethod(method)}
                  type="button"
                >
                  {method === "COD" ? "Thanh toán tại bàn" : "VietQR"}
                </button>
              ))}
            </div>
          </div>

          {errorMessage ? <p className="cmc-inline-error">{errorMessage}</p> : null}

          {successOrder ? (
            <div className="cmc-success-state" role="status">
              <strong>Đã tạo đơn {successOrder.orderCode}</strong>
              <span>
                Trạng thái: {successOrder.status} / Thanh toán: {successOrder.paymentStatus}
              </span>
              <Link to={`/orders/${successOrder.orderCode}`}>Theo dõi đơn</Link>
            </div>
          ) : null}

          {vietQrPayment ? (
            <div className="cmc-success-state" role="status">
              <strong>VietQR đã sẵn sàng</strong>
              <span>
                {formatVnd(vietQrPayment.amount)} - Nội dung: {vietQrPayment.transferContent}
              </span>
              <img alt={`VietQR ${vietQrPayment.orderCode}`} src={vietQrPayment.qrImageDataUri} />
              <a href={vietQrPayment.quickLink} target="_blank" rel="noreferrer">
                Mở link thanh toán
              </a>
            </div>
          ) : null}

          <button className="cmc-submit-order" disabled={!canSubmit} type="submit">
            {isSubmitting ? "Đang gửi đơn..." : "Gửi đơn cho bếp"}
          </button>
        </form>
      </div>
    </section>
  );
}
