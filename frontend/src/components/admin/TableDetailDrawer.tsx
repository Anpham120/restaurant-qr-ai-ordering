import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import type { TableFloorRow } from "./floorMapUtils";
import { X } from "lucide-react";
import "../operations/operations.css";
import "./floor-map.css";

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

type TableDetailDrawerProps = {
  row: TableFloorRow | null;
  onClose: () => void;
  onCloseSession?: (sessionId: string, tableCode: string) => void;
  closingSessionId?: string | null;
};

export function TableDetailDrawer({
  row,
  onClose,
  onCloseSession,
  closingSessionId,
}: TableDetailDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!row) return;
    closeButtonRef.current?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [row, onClose]);

  if (!row) return null;

  const { table, session, state } = row;

  return (
    <div className="floor-drawer-overlay" onClick={onClose}>
      <aside
        className="floor-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="floor-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="floor-drawer-header">
          <div>
            <p className="floor-drawer-kicker">Bàn {table.tableCode}</p>
            <h2 id="floor-drawer-title">{table.displayName}</h2>
          </div>
          <button ref={closeButtonRef} type="button" className="ops-modal-close" aria-label="Đóng" onClick={onClose}>
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <div className="floor-drawer-body">
          <span className={`floor-drawer-badge floor-drawer-badge--${state}`}>
            {state === "inactive" ? "Tạm ngưng" : state === "free" ? "Trống" : state === "payment" ? "Chờ thu" : "Đang phục vụ"}
          </span>

          {session ? (
            <dl className="floor-drawer-meta">
              <div>
                <dt>Mở phiên</dt>
                <dd>{formatTime(session.openedAt)}</dd>
              </div>
              <div>
                <dt>Hết hạn</dt>
                <dd>{formatTime(session.expiresAt)}</dd>
              </div>
              <div>
                <dt>Đơn đang xử lý</dt>
                <dd>{session.activeOrderCount}</dd>
              </div>
            </dl>
          ) : (
            <p className="floor-drawer-empty">Chưa có phiên mở. Khách quét QR trên bàn để đặt món.</p>
          )}

          <div className="floor-drawer-actions">
            {session && onCloseSession ? (
              <button
                type="button"
                className="ops-btn ops-btn--danger"
                disabled={closingSessionId === session.sessionId}
                onClick={() => onCloseSession(session.sessionId, session.tableCode)}
              >
                {closingSessionId === session.sessionId ? "Đang đóng..." : "Đóng phiên"}
              </button>
            ) : null}
            <Link className="ops-btn ops-btn--ghost" to={`/tables?tab=qr&table=${table.tableCode}`}>
              Xem QR
            </Link>
            {state === "payment" || session ? (
              <Link
                className="ops-btn ops-btn--primary"
                to={`/counter?tab=payments&table=${encodeURIComponent(table.tableCode)}`}
              >
                Quầy thu ngân
              </Link>
            ) : null}
            <Link className="ops-btn ops-btn--ghost" to={`/orders?tab=kanban&table=${table.tableCode}`}>
              Xem đơn bàn
            </Link>
          </div>
        </div>
      </aside>
    </div>
  );
}
