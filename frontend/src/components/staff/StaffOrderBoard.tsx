import { useEffect, useMemo, useState } from "react";
import {
  confirmOrderPayment,
  getKitchenOrders,
  updateOrderStatus,
} from "../../services/orderService";
import type { OrderTrackingOrder } from "../../types";

type StaffTicketStatus = "Ready" | "Served" | "PaymentPending" | "Completed";

type StaffTicket = {
  id: string;
  orderCode: string;
  tableLabel: string;
  customerNote: string;
  status: StaffTicketStatus;
  payment: "COD" | "Paid" | "VietQR";
  items: Array<{
    name: string;
    quantity: number;
  }>;
};

const lanes: Array<{
  status: StaffTicketStatus;
  title: string;
  hint: string;
}> = [
  { status: "Ready", title: "Sẵn sàng phục vụ", hint: "Nhận món Ready từ bếp và mang ra bàn." },
  { status: "Served", title: "Đã phục vụ", hint: "Theo dõi phản hồi và chuẩn bị thanh toán." },
  { status: "PaymentPending", title: "Chờ thu tiền", hint: "COD/VietQR cần xác nhận thu ngân." },
  { status: "Completed", title: "Hoàn tất", hint: "Đơn đã kết thúc trong ca." },
];

function toTicket(order: OrderTrackingOrder): StaffTicket | null {
  const paid = order.paymentStatus === "Paid" || order.paymentStatus === "Confirmed";
  let status: StaffTicketStatus | null = null;

  if (order.status === "Ready") {
    status = "Ready";
  } else if (order.status === "Served" && !paid) {
    status = "PaymentPending";
  } else if (order.status === "Served") {
    status = "Served";
  } else if (order.status === "Completed" || paid) {
    status = "Completed";
  }

  if (!status) {
    return null;
  }

  return {
    id: order.orderId,
    orderCode: order.orderCode,
    tableLabel: order.tableCode ? `Bàn ${order.tableCode}` : "Chưa có bàn",
    customerNote: "Không có ghi chú.",
    status,
    payment: paid ? "Paid" : order.paymentMethod,
    items: order.items.map((item) => ({ name: item.name, quantity: item.quantity })),
  };
}

export function StaffOrderBoard() {
  const [tickets, setTickets] = useState<StaffTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reloadTickets() {
    const orders = await getKitchenOrders();
    setTickets(orders.map(toTicket).filter((ticket): ticket is StaffTicket => Boolean(ticket)));
  }

  useEffect(() => {
    reloadTickets()
      .catch(() => setError("Không tải được danh sách đơn cho nhân viên phục vụ."))
      .finally(() => setIsLoading(false));
  }, []);

  const summary = useMemo(
    () => ({
      ready: tickets.filter((ticket) => ticket.status === "Ready").length,
      payment: tickets.filter((ticket) => ticket.status === "PaymentPending").length,
      completed: tickets.filter((ticket) => ticket.status === "Completed").length,
    }),
    [tickets],
  );

  async function serveTicket(ticket: StaffTicket) {
    await updateOrderStatus(ticket.orderCode, "Served");
    await reloadTickets();
  }

  async function completeTicket(ticket: StaffTicket) {
    if (ticket.payment !== "Paid") {
      await confirmOrderPayment(ticket.orderCode, "Xác nhận từ nhân viên phục vụ");
    }
    await updateOrderStatus(ticket.orderCode, "Completed");
    await reloadTickets();
  }

  if (isLoading) {
    return <div className="staff-workspace"><p>Đang tải đơn phục vụ...</p></div>;
  }

  if (error) {
    return <div className="staff-workspace"><p>{error}</p></div>;
  }

  return (
    <div className="staff-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">Trạm phục vụ</span>
          <h3>Luồng phục vụ theo bàn</h3>
          <p>Nhận món từ bếp, đánh dấu đã phục vụ, xác nhận thanh toán và hoàn tất đơn.</p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{summary.ready} món cần mang ra</span>
          <span>{summary.payment} đơn chờ thu tiền</span>
          <span>{summary.completed} hoàn tất</span>
        </div>
      </section>

      <section className="staff-board" aria-label="Bảng đơn phục vụ">
        {lanes.map((lane) => {
          const laneTickets = tickets.filter((ticket) => ticket.status === lane.status);

          return (
            <article className="staff-lane" key={lane.status}>
              <div className="realtime-lane-heading">
                <div>
                  <h3>{lane.title}</h3>
                  <p>{lane.hint}</p>
                </div>
                <span>{laneTickets.length}</span>
              </div>

              {laneTickets.length === 0 ? (
                <p className="realtime-empty">Chưa có đơn trong cột này.</p>
              ) : (
                laneTickets.map((ticket) => (
                  <div className="staff-ticket" key={ticket.id}>
                    <div className="staff-ticket-meta">
                      <span>{ticket.orderCode}</span>
                      <strong>{ticket.tableLabel}</strong>
                      <small>{ticket.payment === "Paid" ? "Đã thanh toán" : ticket.payment}</small>
                    </div>
                    <ul>
                      {ticket.items.map((item) => (
                        <li key={ticket.id + item.name}>
                          <span>{item.name}</span>
                          <b>x{item.quantity}</b>
                        </li>
                      ))}
                    </ul>
                    <p>{ticket.customerNote}</p>
                    <div className="staff-action-row">
                      {ticket.status === "Ready" ? (
                        <button className="button primary" type="button" onClick={() => serveTicket(ticket)}>
                          Đã phục vụ
                        </button>
                      ) : null}
                      {ticket.status === "Served" || ticket.status === "PaymentPending" ? (
                        <button className="button primary" type="button" onClick={() => completeTicket(ticket)}>
                          Hoàn tất đơn
                        </button>
                      ) : null}
                      <button className="button" type="button" onClick={reloadTickets}>
                        Tải lại
                      </button>
                    </div>
                  </div>
                ))
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}
