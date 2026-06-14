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
import { fetchCustomerMenu, getCustomerMenu } from "../../services/menuService";
import type { CustomerMenuResponse } from "../../services/menuService";
import { createOrder, generateVietQrPayment } from "../../services/orderService";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  CustomerOrderType,
  MenuCart,
  MenuItem,
  PaymentMethod,
  VietQrPaymentResponse,
} from "../../types";

const initialMenu: CustomerMenuResponse =
  import.meta.env.VITE_USE_MOCK_MENU === "true"
    ? getCustomerMenu()
    : { categories: [], items: [] };

type CheckoutForm = {
  contactName: string;
  phoneNumber: string;
};

type ActiveOrderType = Extract<CustomerOrderType, "DineIn" | "Pickup">;

const orderTypeCopy: Record<
  ActiveOrderType,
  { label: string; shortLabel: string; description: string }
> = {
  DineIn: {
    label: "Ăn tại bàn",
    shortLabel: "Tại bàn",
    description: "Gửi đơn kèm mã bàn QR để nhân viên và bếp nhận đúng vị trí phục vụ.",
  },
  Pickup: {
    label: "Mang về",
    shortLabel: "Mang về",
    description: "Khách để lại tên và số điện thoại để nhà hàng xác nhận khi món sẵn sàng.",
  },
};

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function getInitialOrderType(): ActiveOrderType {
  if (typeof window === "undefined") {
    return "Pickup";
  }

  return loadOrderContext().tableCode ? "DineIn" : "Pickup";
}

function getStoredTableCode() {
  if (typeof window === "undefined") {
    return undefined;
  }

  return loadOrderContext().tableCode;
}

function getCartItems(cart: MenuCart, items: MenuItem[]) {
  return items.filter((item) => (cart[item.id] ?? 0) > 0);
}

function buildOrderPayload(
  orderType: ActiveOrderType,
  tableCode: string | undefined,
  cart: MenuCart,
  selectedItems: MenuItem[],
  paymentMethod: PaymentMethod,
): CreateOrderRequest {
  return {
    orderType,
    tableCode: orderType === "DineIn" ? tableCode ?? null : null,
    paymentMethod,
    deliveryInfo: null,
    items: selectedItems.map((item) => ({
      menuItemId: item.id,
      quantity: cart[item.id] ?? 0,
    })),
  };
}

export function CustomerCartPage() {
  const [customerMenu, setCustomerMenu] = useState(initialMenu);
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [orderType, setOrderType] = useState<ActiveOrderType>(getInitialOrderType);
  const [tableCode] = useState(getStoredTableCode);
  const [form, setForm] = useState<CheckoutForm>({
    contactName: "",
    phoneNumber: "",
  });
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("COD");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successOrder, setSuccessOrder] = useState<CreateOrderResponse | null>(null);
  const [vietQrPayment, setVietQrPayment] = useState<VietQrPaymentResponse | null>(null);
  const [submittedPayload, setSubmittedPayload] = useState<CreateOrderRequest | null>(null);

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

  const menuItems = customerMenu.items;
  const selectedItems = useMemo(() => getCartItems(cart, menuItems), [cart, menuItems]);
  const unavailableItems = selectedItems.filter((item) => !item.isAvailable);
  const totalPrice = selectedItems.reduce(
    (total, item) => total + (cart[item.id] ?? 0) * item.price,
    0,
  );
  const requiresContact = orderType === "Pickup";
  const orderTypeDetails = orderTypeCopy[orderType];
  const isContactMissing =
    requiresContact && (form.contactName.trim().length === 0 || form.phoneNumber.trim().length === 0);
  const isDineInMissingTable = orderType === "DineIn" && !tableCode;
  const canSubmit =
    selectedItems.length > 0 &&
    unavailableItems.length === 0 &&
    !isContactMissing &&
    !isDineInMissingTable &&
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
    setSubmittedPayload(null);
  }

  function updateForm(field: keyof CheckoutForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setSuccessOrder(null);
    setVietQrPayment(null);

    if (!canSubmit) {
      setErrorMessage("Vui lòng kiểm tra giỏ hàng và thông tin nhận đơn trước khi gửi.");
      return;
    }

    const payload = buildOrderPayload(orderType, tableCode, cart, selectedItems, paymentMethod);
    setIsSubmitting(true);
    setSubmittedPayload(payload);

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
          <p className="cmc-kicker">Giỏ hàng & thanh toán</p>
          <h2>
            Kiểm tra món và <span>gửi đơn cho CMC</span>
          </h2>
          <p>
            Kiểm tra giỏ, chọn hình thức nhận món và gửi đơn cho nhà hàng.
            Sau khi đặt, khách có thể theo dõi trạng thái món theo thời gian thực.
          </p>
          <div className="cmc-hero-actions">
            <Link className="cmc-secondary-link" to={tableCode ? `/table/${tableCode}` : "/menu"}>
              Thêm món khác
            </Link>
            {tableCode ? <span className="cmc-table-badge">Bàn {tableCode}</span> : null}
          </div>
        </div>
      </header>

      <div className="cmc-checkout-layout">
        <div className="cmc-cart-panel" aria-label="Cart details">
          <div className="cmc-section-title">
            <h3>Món đã chọn</h3>
            <span>{selectedItems.length} món</span>
          </div>

          {selectedItems.length === 0 ? (
            <div className="cmc-empty-state">
              Giỏ hàng đang trống. Quay lại thực đơn để chọn món.
            </div>
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
            <h3>Thông tin đặt món</h3>
            <span>{orderTypeDetails.shortLabel}</span>
          </div>

          <div className="cmc-order-type-tabs" role="tablist" aria-label="Order type">
            {(["DineIn", "Pickup"] as ActiveOrderType[]).map((type) => (
              <button
                aria-selected={orderType === type}
                className={orderType === type ? "active" : ""}
                key={type}
                onClick={() => setOrderType(type)}
                type="button"
              >
                {orderTypeCopy[type].label}
              </button>
            ))}
          </div>

          <div className="cmc-checkout-note">
            <strong>{orderTypeDetails.label}</strong>
            <span>{orderTypeDetails.description}</span>
          </div>

          {isDineInMissingTable ? (
            <p className="cmc-inline-error">
              Đơn tại bàn cần mã bàn từ QR. Hãy vào lại đường dẫn `/table/:tableCode` hoặc chọn
              mang về.
            </p>
          ) : null}

          {orderType === "DineIn" ? (
            <div className="cmc-checkout-note">
              <strong>Đơn tại bàn</strong>
              <span>Mã bàn gửi kèm đơn: {tableCode ?? "chưa có"}</span>
            </div>
          ) : null}

          {requiresContact ? (
            <div className="cmc-form-grid">
              <label>
                Tên người nhận
                <input
                  onChange={(event) => updateForm("contactName", event.target.value)}
                  placeholder="Ví dụ: Anh Minh"
                  type="text"
                  value={form.contactName}
                />
              </label>
              <label>
                Số điện thoại
                <input
                  onChange={(event) => updateForm("phoneNumber", event.target.value)}
                  placeholder="0901234567"
                  type="tel"
                  value={form.phoneNumber}
                />
              </label>
            </div>
          ) : null}


          <div className="cmc-checkout-note">
            <strong>Phương thức thanh toán</strong>
            <div className="cmc-order-type-tabs" role="tablist" aria-label="Payment method">
              {(["COD", "VietQR"] as PaymentMethod[]).map((method) => (
                <button
                  aria-selected={paymentMethod === method}
                  className={paymentMethod === method ? "active" : ""}
                  key={method}
                  onClick={() => setPaymentMethod(method)}
                  type="button"
                >
                  {method === "COD" ? "Thanh toán tại quầy" : "VietQR"}
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
              <span>{formatVnd(vietQrPayment.amount)} - Nội dung: {vietQrPayment.transferContent}</span>
              <img alt={`VietQR ${vietQrPayment.orderCode}`} src={vietQrPayment.qrImageDataUri} />
              <a href={vietQrPayment.quickLink} target="_blank" rel="noreferrer">Mở link thanh toán</a>
            </div>
          ) : null}

          <button className="cmc-submit-order" disabled={!canSubmit} type="submit">
            {isSubmitting ? "Đang gửi đơn..." : "Gửi đơn đặt món"}
          </button>

          {submittedPayload ? (
            <p className="cmc-checkout-note small">
              Đã gửi {orderTypeCopy[submittedPayload.orderType as ActiveOrderType].label.toLowerCase()} với{" "}
              {submittedPayload.items.length} dòng món.
            </p>
          ) : null}
        </form>
      </div>
    </section>
  );
}
