import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import "../../../components/order-tracking/realtime-order.css";
import { getOrderTracking } from "../../../services/orderService";
import type {
  OrderItemStatus,
  OrderStatus,
  OrderTrackingItem,
  OrderTrackingOrder,
} from "../../../types";
import { PageShell } from "../../PageShell";

const orderStatusLabels: Record<OrderStatus, string> = {
  Draft: "Đang tạo",
  Placed: "Đã ghi nhận",
  Confirmed: "Đã xác nhận",
  Preparing: "Đang chuẩn bị",
  Ready: "Sẵn sàng phục vụ",
  Served: "Đã phục vụ",
  Delivering: "Đang giao",
  Delivered: "Đã giao",
  Completed: "Hoàn tất",
  Cancelled: "Đã hủy",
};

const paymentStatusLabels: Record<string, string> = {
  Unpaid: "Chưa thanh toán",
  Pending: "Đang chờ đối soát",
  Paid: "Đã thanh toán",
  Confirmed: "Đã xác nhận",
  Failed: "Thanh toán lỗi",
  Cancelled: "Đã hủy",
};

const itemStatusDescriptions: Record<OrderItemStatus, string> = {
  Pending: "Bếp đã nhận món và đang xếp hàng xử lý.",
  Preparing: "Đầu bếp đang chế biến món này.",
  Ready: "Món đã sẵn sàng để phục vụ.",
  Served: "Món đã được phục vụ.",
  Cancelled: "Món đã hủy.",
};

const timelineLabels: Record<string, string> = {
  Placed: "Đã ghi nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Hoàn tất",
};

export function OrderTrackingPage() {
  const { orderCode = "" } = useParams();
  const [order, setOrder] = useState<OrderTrackingOrder | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    if (!orderCode) {
      setErrorMessage("Không tìm thấy mã đơn hàng.");
      setIsLoading(false);
      return;
    }

    let isMounted = true;

    async function loadOrder(showLoading: boolean) {
      if (showLoading) {
        setIsLoading(true);
      }

      try {
        const nextOrder = await getOrderTracking(orderCode);
        if (!isMounted) {
          return;
        }

        setOrder(nextOrder);
        setLastUpdatedAt(new Date().toISOString());
        setErrorMessage("");
      } catch {
        if (isMounted) {
          setErrorMessage("Không tải được trạng thái đơn hàng. Vui lòng thử lại sau.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadOrder(true);
    const intervalId = window.setInterval(() => {
      void loadOrder(false);
    }, 10000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [orderCode]);

  const stats = useMemo(() => {
    const items = order?.items ?? [];

    return [
      {
        label: "Trạng thái đơn",
        value: order ? orderStatusLabels[order.status] : "Đang tải",
        detail: "Cập nhật tự động sau mỗi 10 giây",
      },
      {
        label: "Món đang bếp",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Các món đang được chế biến",
      },
      {
        label: "Thanh toán",
        value: order ? paymentStatusLabels[order.paymentStatus] ?? order.paymentStatus : "Đang tải",
        detail: order?.paymentMethod === "VietQR" ? "Theo dõi đối soát VietQR" : "Thanh toán tại quầy",
      },
    ];
  }, [order]);

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title={orderCode ? `Đơn ${orderCode}` : "Theo dõi đơn"}
      description="Khách theo dõi trạng thái từng món và trạng thái thanh toán sau khi gửi đơn."
      stats={stats}
    >
      <section className="realtime-status-bar">
        <div>
          <strong>Theo dõi đơn hàng</strong>
          <p>
            {lastUpdatedAt
              ? `Cập nhật gần nhất: ${new Date(lastUpdatedAt).toLocaleTimeString("vi-VN")}`
              : "Đang lấy trạng thái mới nhất từ hệ thống."}
          </p>
        </div>
        <button onClick={() => window.location.reload()} type="button">
          Tải lại
        </button>
      </section>

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}
      {isLoading ? <p>Đang tải đơn hàng...</p> : null}
      {!isLoading && order ? <CustomerOrderTrackingPanel order={order} /> : null}
      {!isLoading && !order && !errorMessage ? (
        <section className="tracking-summary-card">
          <div>
            <p className="tracking-kicker">Chưa có đơn</p>
            <h3>Không tìm thấy thông tin đơn hàng</h3>
            <span>Hãy quay lại thực đơn để tạo đơn mới.</span>
          </div>
          <Link className="cmc-secondary-link" to="/menu">
            Xem thực đơn
          </Link>
        </section>
      ) : null}
    </PageShell>
  );
}

function CustomerOrderTrackingPanel({ order }: { order: OrderTrackingOrder }) {
  const readyCount = order.items.filter((item) => item.status === "Ready").length;

  return (
    <section className="order-tracking-panel" aria-label="Theo dõi đơn hàng">
      <div className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Order tracking</p>
          <h3>{order.orderCode}</h3>
          <span>
            {order.tableCode ? `Bàn ${order.tableCode}` : "Mang về"} - {orderStatusLabels[order.status]}
          </span>
        </div>
        <strong>
          {readyCount}/{order.items.length}
          <small> món sẵn sàng</small>
        </strong>
      </div>

      <div className="tracking-timeline">
        {["Placed", "Preparing", "Ready", "Served"].map((status, index) => (
          <div className={getTimelineClass(order.status, status)} key={status}>
            <span>{index + 1}</span>
            <div>
              <h3>{timelineLabels[status]}</h3>
              <p>{getTimelineCopy(status)}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="tracking-item-list">
        {order.items.map((item) => (
          <article className="tracking-item" key={item.orderItemId}>
            <div>
              <strong>{item.name}</strong>
              <p>
                x{item.quantity} - {itemStatusDescriptions[item.status]}
              </p>
            </div>
            <span className={`status-pill status-${item.status.toLowerCase()}`}>
              {getItemStatusLabel(item.status)}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function getItemStatusLabel(status: OrderItemStatus) {
  switch (status) {
    case "Pending":
      return "Đang chờ";
    case "Preparing":
      return "Đang nấu";
    case "Ready":
      return "Sẵn sàng";
    case "Served":
      return "Đã phục vụ";
    default:
      return "Đã hủy";
  }
}

function getTimelineCopy(status: string) {
  switch (status) {
    case "Placed":
      return "Đơn đã được ghi nhận.";
    case "Preparing":
      return "Bếp đang xử lý các món.";
    case "Ready":
      return "Món sẵn sàng để mang ra.";
    default:
      return "Nhân viên xác nhận phục vụ.";
  }
}

function getTimelineClass(currentStatus: string, timelineStatus: string) {
  const order = ["Placed", "Preparing", "Ready", "Served"];
  const currentIndex = order.indexOf(currentStatus);
  const timelineIndex = order.indexOf(timelineStatus);

  return timelineIndex <= currentIndex
    ? "tracking-step tracking-step-active"
    : "tracking-step";
}
