import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  CustomerOrderType,
  MenuCart,
  MenuItem,
  PaymentMethod,
} from "../../types";

type CheckoutForm = {
  contactName: string;
  phoneNumber: string;
  deliveryAddress: string;
  note: string;
};

const orderTypeCopy: Record<
  CustomerOrderType,
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
  DeliveryMock: {
    label: "Giao tận nơi",
    shortLabel: "Giao tận nơi",
    description: "Khách cung cấp địa chỉ nhận món để nhà hàng xử lý theo luồng giao hàng.",
  },
};

const paymentCopy: Record<PaymentMethod, { label: string; description: string }> = {
  COD: {
    label: "Thanh toán tại quầy",
    description: "Khách thanh toán khi nhận món hoặc sau khi dùng bữa.",
  },
  VietQR: {
    label: "VietQR",
    description: "Hệ thống tạo đơn với phương thức VietQR để nhân viên đối soát thanh toán.",
  },
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

function getCartItems(cart: MenuCart, menuItems: MenuItem[]) {
  return menuItems.filter((item) => (cart[item.id] ?? 0) > 0);
}

function buildOrderPayload(
  orderType: CustomerOrderType,
  tableCode: string | undefined,
  paymentMethod: PaymentMethod,
  cart: MenuCart,
  selectedItems: MenuItem[],
  form: CheckoutForm,
): CreateOrderRequest {
  return {
    orderType,
    tableCode: orderType === "DineIn" ? tableCode ?? null : null,
    paymentMethod,
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
  const navigate = useNavigate();
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [isMenuLoading, setIsMenuLoading] = useState(true);
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [orderType, setOrderType] = useState<CustomerOrderType>(getInitialOrderType);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("COD");
  const [tableCode] = useState(getStoredTableCode);
  const [form, setForm] = useState<CheckoutForm>({
    contactName: "",
    phoneNumber: "",
    deliveryAddress: "",
    note: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    getCustomerMenu()
      .then((menu) => {
        if (isMounted) {
          setMenuItems(menu.items);
        }
      })
      .catch((error) => {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Không tải được thực đơn.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsMenuLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const selectedItems = useMemo(() => getCartItems(cart, menuItems), [cart, menuItems]);
  const unavailableItems = selectedItems.filter((item) => !item.isAvailable);
  const totalPrice = selectedItems.reduce(
    (total, item) => total + (cart[item.id] ?? 0) * item.price,
    0,
  );
  const requiresContact = orderType === "Pickup" || orderType === "DeliveryMock";
  const requiresDelivery = orderType === "DeliveryMock";
  const orderTypeDetails = orderTypeCopy[orderType];
  const paymentDetails = paymentCopy[paymentMethod];
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
    !isMenuLoading &&
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
  }

  function updateForm(field: keyof CheckoutForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");

    if (!canSubmit) {
      setErrorMessage("Vui lòng kiểm tra giỏ hàng và thông tin nhận đơn trước khi gửi.");
      return;
    }

    const payload = buildOrderPayload(orderType, tableCode, paymentMethod, cart, selectedItems, form);
    setIsSubmitting(true);

    try {
      const response = await createOrder(payload);
      setCart({});
      clearMenuCart();
      navigate(`/orders/${response.orderCode}`, {
        state: {
          paymentMethod,
          paymentStatus: response.paymentStatus,
        },
      });
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
          <p className="cmc-kicker">Giỏ hàng và thanh toán</p>
          <h2>
            Kiểm tra món và <span>gửi đơn cho CMC</span>
          </h2>
          <p>
            Chọn hình thức nhận món, phương thức thanh toán và gửi đơn để bếp xử lý trên hệ thống.
            Sau khi đặt, khách được chuyển sang màn hình theo dõi trạng thái.
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
        <div className="cmc-cart-panel" aria-label="Chi tiết giỏ hàng">
          <div className="cmc-section-title">
            <h3>Món đã chọn</h3>
            <span>{selectedItems.length} món</span>
          </div>

          {isMenuLoading ? <div className="cmc-empty-state">Đang tải giỏ hàng...</div> : null}

          {!isMenuLoading && selectedItems.length === 0 ? (
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

          <div className="cmc-order-type-tabs" role="tablist" aria-label="Hình thức nhận món">
            {(["DineIn", "Pickup", "DeliveryMock"] as CustomerOrderType[]).map((type) => (
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
              Đơn tại bàn cần mã bàn từ QR. Hãy vào lại đường dẫn mã bàn hoặc chọn mang về.
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

          <div className="cmc-section-title">
            <h3>Thanh toán</h3>
            <span>{paymentDetails.label}</span>
          </div>
          <div className="cmc-order-type-tabs" role="tablist" aria-label="Phương thức thanh toán">
            {(["COD", "VietQR"] as PaymentMethod[]).map((method) => (
              <button
                aria-selected={paymentMethod === method}
                className={paymentMethod === method ? "active" : ""}
                key={method}
                onClick={() => setPaymentMethod(method)}
                type="button"
              >
                {paymentCopy[method].label}
              </button>
            ))}
          </div>
          <div className="cmc-checkout-note">
            <strong>{paymentDetails.label}</strong>
            <span>{paymentDetails.description}</span>
          </div>

          {errorMessage ? <p className="cmc-inline-error">{errorMessage}</p> : null}

          <button className="cmc-submit-order" disabled={!canSubmit} type="submit">
            {isSubmitting ? "Đang gửi đơn..." : "Gửi đơn đặt món"}
          </button>
        </form>
      </div>
    </section>
  );
}
