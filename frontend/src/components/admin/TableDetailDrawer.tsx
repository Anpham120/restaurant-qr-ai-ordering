import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { TableFloorRow } from "./floorMapUtils";
import { ArrowLeft, X } from "lucide-react";
import { TableQrCode } from "../qr/TableQrCode";
import { buildOrderingLink } from "../../utils/tableOrderingLink";
import "../operations/operations.css";
import "./floor-map.css";

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

type DrawerView = "details" | "qr";

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
  const viewRef = useRef<DrawerView>("details");
  const [view, setView] = useState<DrawerView>("details");
  const [copyState, setCopyState] = useState<"idle" | "success" | "error">("idle");

  viewRef.current = view;

  useEffect(() => {
    setView("details");
    setCopyState("idle");
  }, [row?.table.tableCode]);

  useEffect(() => {
    if (!row) return;
    closeButtonRef.current?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (viewRef.current === "qr") {
        setView("details");
        return;
      }
      onClose();
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
  const orderingLink = buildOrderingLink(table);

  function openQrView() {
    setView("qr");
    setCopyState("idle");
  }

  async function copyTableLink() {
    try {
      await navigator.clipboard.writeText(orderingLink);
      setCopyState("success");
    } catch {
      setCopyState("error");
    }
  }

  return (
    <div className="floor-drawer-overlay" onClick={onClose}>
      <aside
        className={`floor-drawer${view === "qr" ? " floor-drawer--qr" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="floor-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="floor-drawer-header">
          <div>
            {view === "qr" ? (
              <button type="button" className="floor-drawer-back" onClick={() => setView("details")}>
                <ArrowLeft aria-hidden="true" size={16} />
                Quay lại
              </button>
            ) : (
              <p className="floor-drawer-kicker">Bàn {table.tableCode}</p>
            )}
            <h2 id="floor-drawer-title">
              {view === "qr" ? `QR bàn ${table.tableCode}` : table.displayName}
            </h2>
          </div>
          <button ref={closeButtonRef} type="button" className="ops-modal-close" aria-label="Đóng" onClick={onClose}>
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        {view === "qr" ? (
          <div className="floor-drawer-body floor-drawer-body--qr">
            <div className="floor-drawer-qr-glass">
              <p className="floor-drawer-qr-hint">Khách quét mã này trên bàn để mở phiên đặt món.</p>
              <div className="floor-drawer-qr-frame">
                <TableQrCode
                  downloadName={`qr-ban-${table.tableCode}.png`}
                  label={`QR bàn ${table.tableCode}`}
                  value={orderingLink}
                />
              </div>
              <div className="floor-drawer-qr-link">
                <span>Link đặt món</span>
                <code title={orderingLink}>{orderingLink}</code>
              </div>
              <div className="floor-drawer-qr-actions">
                <a className="ops-btn ops-btn--ghost" href={orderingLink} rel="noreferrer" target="_blank">
                  Mở trang khách
                </a>
                <button className="ops-btn ops-btn--primary" type="button" onClick={copyTableLink}>
                  {copyState === "success" ? "Đã sao chép" : copyState === "error" ? "Thử lại" : "Sao chép link"}
                </button>
              </div>
              {copyState !== "idle" ? (
                <p
                  className={`floor-drawer-qr-feedback${copyState === "error" ? " is-error" : ""}`}
                  role="status"
                >
                  {copyState === "success"
                    ? "Đã sao chép link vào clipboard."
                    : "Không thể sao chép — thử chọn link thủ công."}
                </p>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="floor-drawer-body">
            <span className={`floor-drawer-badge floor-drawer-badge--${state}`}>
              {state === "inactive"
                ? "Tạm ngưng"
                : state === "free"
                  ? "Trống"
                  : state === "payment"
                    ? "Chờ thu"
                    : "Đang phục vụ"}
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
              <button type="button" className="ops-btn ops-btn--ghost" onClick={openQrView}>
                Xem QR
              </button>
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
        )}
      </aside>
    </div>
  );
}
