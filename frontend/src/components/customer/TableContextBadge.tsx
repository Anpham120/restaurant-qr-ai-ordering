type TableContextBadgeProps = {
  tableCode?: string;
};

export function TableContextBadge({ tableCode }: TableContextBadgeProps) {
  if (!tableCode) {
    return (
      <span className="cmc-table-badge muted">
        Khách chọn món tại nhà hàng hoặc đặt online
      </span>
    );
  }

  return (
    <span className="cmc-table-badge">
      Bàn {tableCode} · QR dine-in
    </span>
  );
}

