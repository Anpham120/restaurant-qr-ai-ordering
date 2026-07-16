import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  clearMenuCart,
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import "../../components/customer/customer-cart.css";
import { formatVnd } from "../../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../../services/menuService";
import { createOrder, generateVietQrPayment, validatePromotion } from "../../services/orderService";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  MenuCart,
  MenuItem,
  PaymentMethod,
  ValidatePromotionResponse,
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
  promotionCode: string | null,
  customerPhoneNumber: string | null,
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
    promotionCode,
    customerPhoneNumber,
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
  const [promoInput, setPromoInput] = useState("");
  const [phoneInput, setPhoneInput] = useState("");
  const [appliedPromo, setAppliedPromo] = useState<ValidatePromotionResponse | null>(null);
  const [promoError, setPromoError] = useState("");
  const [isApplyingPromo, setIsApplyingPromo] = useState(false);

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
  const discountAmount = appliedPromo?.discountAmount ?? 0;
  const finalTotal = Math.max(0, totalPrice - discountAmount);
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
    // Cart total changed, so any applied promotion must be re-validated.
    setAppliedPromo(null);
    setPromoError("");
  }

  async function applyPromo() {
    const code = promoInput.trim();
    if (!code) {
      setPromoError("Vui lòng nhập mã khuyến mãi.");
      return;
    }
    if (totalPrice <= 0) {
      setPromoError("Giỏ hàng trống, không thể áp dụng mã.");
      return;
    }
    setIsApplyingPromo(true);
    setPromoError("");
    try {
      const result = await validatePromotion(code, totalPrice);
      setAppliedPromo(result);
    } catch (error) {
      setAppliedPromo(null);
      setPromoError(error instanceof Error ? error.message : "Mã khuyến mãi không hợp lệ.");
    } finally {
      setIsApplyingPromo(false);
    }
  }

  function removePromo() {
    setAppliedPromo(null);
    setPromoInput("");
    setPromoError("");
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

    const payload = buildOrderPayload(
      cart,
      selectedItems,
      paymentMethod,
      orderContext,
      appliedPromo?.code ?? null,
      phoneInput.trim() || null,
    );
    setIsSubmitting(true);

    try {
      const response = await createOrder(payload);
      setSuccessOrder(response);
      if (payload.paymentMethod === "VietQR") {
        setVietQrPayment(await generateVietQrPayment(response.orderCode));
      }
      setCart({});
      clearMenuCart();
      setAppliedPromo(null);
      setPromoInput("");
      setPhoneInput("");
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
            <span>Tạm tính</span>
            <strong>{formatVnd(totalPrice)}</strong>
          </div>

          {appliedPromo ? (
            <>
              <div className="cmc-cart-total cmc-cart-total--discount">
                <span>Giảm giá ({appliedPromo.code})</span>
                <strong>-{formatVnd(discountAmount)}</strong>
              </div>
              <div className="cmc-cart-total">
                <span>Thành tiền</span>
                <strong>{formatVnd(finalTotal)}</strong>
              </div>
            </>
          ) : null}

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
                  {method === "COD" ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18" aria-hidden="true">
                      <rect x="2" y="6" width="20" height="12" rx="2" />
                      <circle cx="12" cy="12" r="3" />
                      <path d="M6 12h.01M18 12h.01" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18" aria-hidden="true">
                      <rect x="3" y="3" width="7" height="7" rx="1" />
                      <rect x="14" y="3" width="7" height="7" rx="1" />
                      <rect x="3" y="14" width="7" height="7" rx="1" />
                      <path d="M14 14h3v3h-3zM20 14h1v1h-1zM14 20h1v1h-1zM18 18h3v3h-3z" />
                    </svg>
                  )}
                  {method === "COD" ? "Tiền mặt" : "Chuyển khoản QR"}
                </button>
              ))}
            </div>
          </div>

          <div className="cmc-checkout-note">
            <strong>Mã khuyến mãi</strong>
            <div className="cmc-promo-row">
              <input
                aria-label="Mã khuyến mãi"
                className="cmc-text-input"
                disabled={Boolean(appliedPromo)}
                onChange={(event) => setPromoInput(event.target.value.toUpperCase())}
                placeholder="VD: GIAM10"
                value={promoInput}
              />
              {appliedPromo ? (
                <button className="cmc-promo-btn" onClick={removePromo} type="button">
                  Bỏ mã
                </button>
              ) : (
                <button
                  className="cmc-promo-btn"
                  disabled={isApplyingPromo}
                  onClick={applyPromo}
                  type="button"
                >
                  {isApplyingPromo ? "Đang kiểm tra..." : "Áp dụng"}
                </button>
              )}
            </div>
            {promoError ? <span className="cmc-inline-error">{promoError}</span> : null}
            {appliedPromo ? (
              <span className="cmc-promo-success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="16" height="16" aria-hidden="true">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                Đã áp dụng {appliedPromo.name}
              </span>
            ) : null}
          </div>

          <div className="cmc-checkout-note">
            <strong>Số điện thoại tích điểm (tùy chọn)</strong>
            <input
              aria-label="Số điện thoại tích điểm"
              className="cmc-text-input"
              inputMode="tel"
              onChange={(event) => setPhoneInput(event.target.value)}
              placeholder="VD: 0909xxxxxx"
              value={phoneInput}
            />
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
