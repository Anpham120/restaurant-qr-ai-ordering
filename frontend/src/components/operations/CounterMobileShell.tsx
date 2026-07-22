import { NavLink, useLocation, useSearchParams } from "react-router-dom";
import { Armchair, ClipboardList, Clock3, Receipt } from "lucide-react";
import { useOpsNavBadges } from "./OpsNavBadgesProvider";
import "./operations.css";

const NAV_ITEMS = [
  { to: "/counter?tab=payments", label: "Quầy", icon: Receipt, badgeKey: "counter" as const, matchTab: "payments" },
  { to: "/tables", label: "Bàn", icon: Armchair, badgeKey: "tables" as const, matchPath: "/tables" },
  { to: "/orders", label: "Đơn", icon: ClipboardList, badgeKey: "orders" as const, matchPath: "/orders" },
  { to: "/counter?tab=shift", label: "Ca", icon: Clock3, badgeKey: null, matchTab: "shift" },
];

export function CounterMobileShell() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { badges } = useOpsNavBadges();
  const counterTab = searchParams.get("tab") ?? "payments";

  return (
    <nav className="ops-bottom-nav" aria-label="Điều hướng quầy">
      {NAV_ITEMS.map((item) => {
        const isCounterRoute = location.pathname === "/counter";
        const isActive = item.matchTab
          ? isCounterRoute && counterTab === item.matchTab
          : location.pathname === item.matchPath;
        const badge = item.badgeKey ? badges[item.badgeKey] : 0;
        const Icon = item.icon;
        return (
          <NavLink
            key={item.label}
            to={item.to}
            className={`ops-bottom-nav-link${isActive ? " is-active" : ""}`}
          >
            <span className="ops-bottom-nav-icon">
              <Icon aria-hidden="true" size={18} />
              {badge > 0 ? <span className="ops-bottom-nav-badge">{badge > 99 ? "99+" : badge}</span> : null}
            </span>
            {item.label}
          </NavLink>
        );
      })}
    </nav>
  );
}
