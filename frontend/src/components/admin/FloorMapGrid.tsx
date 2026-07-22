import type { TableFloorRow, FloorMapFilter } from "./floorMapUtils";
import { filterFloorRows } from "./floorMapUtils";
import "./floor-map.css";

const FILTER_LABELS: Record<FloorMapFilter, string> = {
  all: "Tất cả",
  serving: "Đang phục vụ",
  free: "Trống",
  payment: "Cần thu",
};

const STATE_LABELS: Record<TableFloorRow["state"], string> = {
  inactive: "Tạm ngưng",
  free: "Trống",
  serving: "Phục vụ",
  payment: "Chờ thu",
};

type FloorMapGridProps = {
  rows: TableFloorRow[];
  filter: FloorMapFilter;
  onFilterChange: (filter: FloorMapFilter) => void;
  onSelect: (row: TableFloorRow) => void;
  selectedTableCode?: string | null;
};

export function FloorMapGrid({
  rows,
  filter,
  onFilterChange,
  onSelect,
  selectedTableCode,
}: FloorMapGridProps) {
  const visibleRows = filterFloorRows(rows, filter);
  const counts = {
    all: rows.length,
    serving: rows.filter((row) => row.state === "serving").length,
    free: rows.filter((row) => row.state === "free").length,
    payment: rows.filter((row) => row.state === "payment").length,
  };

  return (
    <div className="floor-map">
      <div className="floor-map-filters" role="tablist" aria-label="Lọc sơ đồ bàn">
        {(Object.keys(FILTER_LABELS) as FloorMapFilter[]).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filter === value}
            className={`floor-map-filter${filter === value ? " is-active" : ""}`}
            onClick={() => onFilterChange(value)}
          >
            {FILTER_LABELS[value]} ({counts[value]})
          </button>
        ))}
      </div>

      <div className="floor-map-grid" role="list">
        {visibleRows.map((row) => (
          <button
            key={row.table.tableCode}
            type="button"
            role="listitem"
            className={`floor-map-tile floor-map-tile--${row.state}${selectedTableCode === row.table.tableCode ? " is-selected" : ""}`}
            onClick={() => onSelect(row)}
            aria-label={`Bàn ${row.table.tableCode}, ${STATE_LABELS[row.state]}`}
          >
            <span className="floor-map-tile-code">{row.table.tableCode}</span>
            <span className="floor-map-tile-name">{row.table.displayName}</span>
            <span className="floor-map-tile-state">{STATE_LABELS[row.state]}</span>
            {row.session ? (
              <span className="floor-map-tile-meta">{row.session.activeOrderCount} đơn</span>
            ) : null}
          </button>
        ))}
        {visibleRows.length === 0 ? (
          <div className="ops-empty floor-map-empty">Không có bàn khớp bộ lọc</div>
        ) : null}
      </div>
    </div>
  );
}
