import { Link } from "react-router-dom";
import { BellRing } from "lucide-react";
import type { OpsAssistanceAlert } from "./OpsAssistanceProvider";
import "./operations.css";

type OpsAssistancePanelProps = {
  items: OpsAssistanceAlert[];
  title?: string;
  emptyLabel?: string;
};

export function OpsAssistancePanel({
  items,
  title = "Khách cần hỗ trợ",
  emptyLabel = "Không có yêu cầu hỗ trợ gần đây.",
}: OpsAssistancePanelProps) {
  return (
    <section className="ops-command-widget">
      <div className="ops-command-widget-head">
        <h2><BellRing size={18} /> {title}</h2>
      </div>
      {items.length > 0 ? (
        <ul className="ops-command-list">
          {items.map((item) => (
            <li key={item.id}>
              <Link to={`/tables?tab=sessions&table=${encodeURIComponent(item.tableCode)}`}>
                Bàn {item.tableCode}
                {item.note ? ` · ${item.note}` : ""}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="ops-command-empty">{emptyLabel}</p>
      )}
    </section>
  );
}
