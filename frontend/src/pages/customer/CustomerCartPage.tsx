import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  clearMenuCart,
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import { formatVnd } from "../../components/menu/MenuItemCard";
import { getCustomerMenu } from "../../services/menuService";
import { createOrder } from "../../services/orderService";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  CustomerOrderType,
  MenuCart,
  MenuItem,
} from "../../types";

const customerMenu = getCustomerMenu();
const menuItems = customerMenu.items;

type CheckoutForm = {
  contactName: string;
  phoneNumber: string;
  deliveryAddress: string;
  note: string;
};

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function getInitialOrderType(): CustomerOrderType {
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

function getCartItems(cart: MenuCart) {
  return menuItems.filter((item) => (cart[item.id] ?? 0) > 0);
}

function buildOrderPayload(
  orderType: CustomerOrderType,
  tableCode: string | undefined,
  cart: MenuCart,
  selectedItems: MenuItem[],
  form: CheckoutForm,
): CreateOrderRequest {
  return {
    orderType,
    tableCode: orderType === "DineIn" ? tableCode ?? null : null,
    paymentMethod: "COD",
    deliveryInfo:
      orderType === "DeliveryMock"
        ? {
            recipientName: form.contactName.trim(),
            phoneNumber: form.phoneNumber.trim(),
            address: form.deliveryAddress.trim(),
            note: form.note.trim() || undefined,
          }
        : null,
    items: selectedItems.map((item) => ({
      menuItemId: item.id,
      quantity: cart[item.id] ?? 0,
    })),
  };
}

export function CustomerCartPage() {
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [orderType, setOrderType] = useState<CustomerOrderType>(getInitialOrderType);
  const [tableCode] = useState(getStoredTableCode);
  const [form, setForm] = useState<CheckoutForm>({
    contactName: "",
    phoneNumber: "",
    deliveryAddress: "",
    note: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successOrder, setSuccessOrder] = useState<CreateOrderResponse | null>(null);
  const [submittedPayload, setSubmittedPayload] = useState<CreateOrderRequest | null>(null);

  const selectedItems = useMemo(() => getCartItems(cart), [cart]);
  const unavailableItems = selectedItems.filter((item) => !item.isAvailable);
  const totalPrice = selectedItems.reduce(
    (total, item) => total + (cart[item.id] ?? 0) * item.price,
    0,
  );
  const payloadPreview = buildOrderPayload(orderType, tableCode, cart, selectedItems, form);
  const requiresContact = orderType === "Pickup" || orderType === "DeliveryMock";
  const requiresDelivery = orderType === "DeliveryMock";
  const isContactMissing =
    requiresContact && (form.contactName.trim().length === 0 || form.phoneNumber.trim().length === 0);
  const isDeliveryMissing = requiresDelivery && form.deliveryAddress.trim().length === 0;
  const isDineInMissingTable = orderType === "DineIn" && !tableCode;
  const canSubmit =
    selectedItems.length > 0 &&
    unavailableItems.length === 0 &&
    !isContactMissing &&
    !isDeliveryMissing &&
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
    setSubmittedPayload(null);
  }

  function updateForm(field: keyof CheckoutForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setSuccessOrder(null);

    if (!canSubmit) {
      setErrorMessage("Vui lòng kiểm tra giỏ hàng và thông tin nhận đơn trước khi gửi.");
      return;
    }

    const payload = buildOrderPayload(orderType, tableCode, cart, selectedItems, form);
    setIsSubmitting(true);
    setSubmittedPayload(payload);

    try {
      const response = await createOrder(payload);
      setSuccessOrder(response);
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
            Luồng checkout mock theo contract `POST /api/orders`, sẵn sàng nối backend khi
            endpoint đặt món được mở.
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
            <span>{orderType}</span>
          </div>

          <div className="cmc-order-type-tabs" role="tablist" aria-label="Order type">
            {(["DineIn", "Pickup", "DeliveryMock"] as CustomerOrderType[]).map((type) => (
              <button
                aria-selected={orderType === type}
                className={orderType === type ? "active" : ""}
                key={type}
                onClick={() => setOrderType(type)}
                type="button"
              >
                {type}
              </button>
            ))}
          </div>

          {isDineInMissingTable ? (
            <p className="cmc-inline-error">
              DineIn cần mã bàn từ QR. Hãy vào lại đường dẫn `/table/:tableCode` hoặc chọn Pickup.
            </p>
          ) : null}

          {orderType === "DineIn" ? (
            <div className="cmc-checkout-note">
              <strong>Đơn tại bàn</strong>
              <span>Payload sẽ gửi kèm tableCode: {tableCode ?? "chưa có"}</span>
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

          {requiresDelivery ? (
            <label className="cmc-field-block">
              Địa chỉ giao hàng
              <textarea
                onChange={(event) => updateForm("deliveryAddress", event.target.value)}
                placeholder="Số nhà, đường, phường/xã, quận/huyện"
                rows={3}
                value={form.deliveryAddress}
              />
            </label>
          ) : null}

          <label className="cmc-field-block">
            Ghi chú cho nhà hàng
            <textarea
              onChange={(event) => updateForm("note", event.target.value)}
              placeholder="Ít cay, giao giờ trưa, cần hóa đơn..."
              rows={3}
              value={form.note}
            />
          </label>

          <details className="cmc-payload-preview">
            <summary>Payload createOrder</summary>
            <pre>{JSON.stringify(payloadPreview, null, 2)}</pre>
          </details>

          {errorMessage ? <p className="cmc-inline-error">{errorMessage}</p> : null}

          {successOrder ? (
            <div className="cmc-success-state" role="status">
              <strong>Đã tạo đơn {successOrder.orderCode}</strong>
              <span>Trạng thái: {successOrder.status} / Thanh toán: {successOrder.paymentStatus}</span>
              <Link to={`/orders/${successOrder.orderCode}`}>Theo dõi đơn</Link>
            </div>
          ) : null}

          <button className="cmc-submit-order" disabled={!canSubmit} type="submit">
            {isSubmitting ? "Đang gửi đơn..." : "Gửi đơn đặt món"}
          </button>

          {submittedPayload ? (
            <p className="cmc-checkout-note small">
              Payload cuối đã gửi: {submittedPayload.orderType} - {submittedPayload.items.length} dòng món.
            </p>
          ) : null}
        </form>
      </div>
    </section>
  );
}
