import { useCallback, useEffect, useState } from "react";
import {
  closeCounterShift,
  getCurrentCounterShift,
  openCounterShift,
  type CounterShiftSummary,
} from "../../services/counterShiftService";
import "../../components/operations/operations.css";

const formatVnd = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

export function CounterShiftPanel({ embedded = false }: { embedded?: boolean }) {
  const [shift, setShift] = useState<CounterShiftSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [openingCash, setOpeningCash] = useState("0");
  const [closingCash, setClosingCash] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setShift(await getCurrentCounterShift());
    } catch {
      setNotice("Không tải được thông tin ca quầy.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleOpenShift() {
    const balance = Number.parseFloat(openingCash.replace(/[^\d.-]/g, "")) || 0;
    try {
      setShift(await openCounterShift(balance));
      setNotice("Đã mở ca quầy.");
    } catch {
      setNotice("Không mở được ca. Kiểm tra ca đang mở.");
    }
  }

  async function handleCloseShift() {
    if (!shift) return;
    const actual = Number.parseFloat(closingCash.replace(/[^\d.-]/g, ""));
    if (Number.isNaN(actual)) {
      setNotice("Nhập số tiền thực tế trong két.");
      return;
    }
    try {
      setShift(await closeCounterShift(shift.shiftId, actual));
      setClosingCash("");
      setNotice("Đã chốt ca quầy.");
    } catch {
      setNotice("Chốt ca thất bại.");
    }
  }

  if (loading) {
    return <div className="ops-notice ops-notice--info">Đang tải ca quầy…</div>;
  }

  return (
    <section className="counter-shift-panel" style={{ marginBottom: 20 }}>
      {!embedded ? (
        <div className="ops-page-header">
          <h2 style={{ margin: 0 }}>Ca quầy</h2>
          <p style={{ margin: "4px 0 0" }}>Mở ca trước khi thu tiền, chốt ca cuối phiên</p>
        </div>
      ) : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}
      {shift?.status === "Open" ? (
        <div className="ops-stats">
          <div className="ops-stat-card">
            <div className="ops-stat-label">Mở ca lúc</div>
            <div className="ops-stat-value">{new Date(shift.openedAt).toLocaleTimeString("vi-VN")}</div>
            <div className="ops-stat-detail">{shift.openedByName}</div>
          </div>
          <div className="ops-stat-card">
            <div className="ops-stat-label">Tiền đầu ca</div>
            <div className="ops-stat-value">{formatVnd(shift.openingCashBalance)}</div>
          </div>
          <div className="ops-stat-card">
            <div className="ops-stat-label">Dự kiến trong két</div>
            <div className="ops-stat-value">{formatVnd(shift.expectedCashTotal)}</div>
          </div>
        </div>
      ) : null}
      {shift?.status === "Open" ? (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
          <label>
            Tiền thực tế khi chốt ca
            <input value={closingCash} onChange={(event) => setClosingCash(event.target.value)} placeholder="VD: 2500000" />
          </label>
          <button className="ops-btn ops-btn--primary" type="button" onClick={() => void handleCloseShift()}>
            Chốt ca
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
          <label>
            Tiền đầu ca
            <input value={openingCash} onChange={(event) => setOpeningCash(event.target.value)} placeholder="0" />
          </label>
          <button className="ops-btn ops-btn--primary" type="button" onClick={() => void handleOpenShift()}>
            Mở ca
          </button>
        </div>
      )}
    </section>
  );
}
