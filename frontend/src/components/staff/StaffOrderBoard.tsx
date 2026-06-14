import { useMemo, useState } from "react";

type StaffTicketStatus = "Ready" | "Served" | "PaymentPending" | "Completed";

type StaffTicket = {
  id: string;
  orderCode: string;
  tableLabel: string;
  customerNote: string;
  status: StaffTicketStatus;
  payment: "COD" | "Paid";
  items: Array<{
    name: string;
    quantity: number;
  }>;
};

const initialTickets: StaffTicket[] = [
  {
    id: "staff-001",
    orderCode: "ORDER-001",
    tableLabel: "Bàn T05",
    customerNote: "Mang nước trước, ít đá.",
    status: "Ready",
    payment: "COD",
    items: [
      { name: "Gỏi cuốn tôm thịt", quantity: 2 },
      { name: "Trà đào cam sả", quantity: 2 },
    ],
  },
  {
    id: "staff-002",
    orderCode: "ORDER-002",
    tableLabel: "Pickup - Anh Minh",
    customerNote: "Đóng gói riêng nước chấm.",
    status: "Served",
    payment: "COD",
    items: [
      { name: "Bò lúc lắc", quantity: 1 },
      { name: "Nem rán Hà Nội", quantity: 2 },
    ],
  },
  {
    id: "staff-003",
    orderCode: "ORDER-003",
    tableLabel: "Giao hàng",
    customerNote: "Đơn giao hàng đã thanh toán.",
    status: "Completed",
    payment: "Paid",
    items: [{ name: "Lẩu Thái hải sản", quantity: 1 }],
  },
];

const lanes: Array<{
  status: StaffTicketStatus;
  title: string;
  hint: string;
}> = [
  { status: "Ready", title: "Sẵn sàng phục vụ", hint: "Nhận món từ bếp và mang ra bàn." },
  { status: "Served", title: "Đã phục vụ", hint: "Theo dõi phản hồi và chuẩn bị thanh toán." },
  { status: "PaymentPending", title: "Chờ thu tiền", hint: "COD cần xác nhận thu ngân." },
  { status: "Completed", title: "Hoàn tất", hint: "Đơn đã kết thúc trong ca." },
];

export function StaffOrderBoard() {
  const [tickets, setTickets] = useState(initialTickets);

  const summary = useMemo(
    () => ({
      ready: tickets.filter((ticket) => ticket.status === "Ready").length,
      payment: tickets.filter((ticket) => ticket.status === "PaymentPending").length,
      completed: tickets.filter((ticket) => ticket.status === "Completed").length,
    }),
    [tickets],
  );

  function moveTicket(ticketId: string, status: StaffTicketStatus) {
    setTickets((current) =>
      current.map((ticket) => (ticket.id === ticketId ? { ...ticket, status } : ticket)),
    );
  }

  return (
    <div className="staff-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">Staff station</span>
          <h3>Luồng phục vụ rõ trạng thái</h3>
          <p>
            Nhân viên nhận món Ready từ bếp, đánh dấu đã phục vụ, rồi chuyển sang
            thu COD hoặc hoàn tất nếu đã thanh toán.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{summary.ready} món cần mang ra</span>
          <span>{summary.payment} đơn chờ COD</span>
          <span>{summary.completed} hoàn tất</span>
        </div>
      </section>

      <section className="staff-board" aria-label="Staff order board">
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
                      <small>{ticket.payment === "Paid" ? "Đã thanh toán" : "COD"}</small>
                    </div>
                    <ul>
                      {ticket.items.map((item) => (
                        <li key={item.name}>
                          <span>{item.name}</span>
                          <b>x{item.quantity}</b>
                        </li>
                      ))}
                    </ul>
                    <p>{ticket.customerNote}</p>
                    <div className="staff-action-row">
                      {ticket.status === "Ready" ? (
                        <button
                          className="button primary"
                          type="button"
                          onClick={() => moveTicket(ticket.id, "Served")}
                        >
                          Đã phục vụ
                        </button>
                      ) : null}
                      {ticket.status === "Served" && ticket.payment === "COD" ? (
                        <button
                          className="button primary"
                          type="button"
                          onClick={() => moveTicket(ticket.id, "PaymentPending")}
                        >
                          Chuyển thu COD
                        </button>
                      ) : null}
                      {ticket.status === "Served" && ticket.payment === "Paid" ? (
                        <button
                          className="button primary"
                          type="button"
                          onClick={() => moveTicket(ticket.id, "Completed")}
                        >
                          Hoàn tất
                        </button>
                      ) : null}
                      {ticket.status === "PaymentPending" ? (
                        <button
                          className="button primary"
                          type="button"
                          onClick={() => moveTicket(ticket.id, "Completed")}
                        >
                          Đã thu tiền
                        </button>
                      ) : null}
                      <button className="button" type="button">
                        Ghi chú
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
