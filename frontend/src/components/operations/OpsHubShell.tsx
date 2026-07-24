import type { ReactNode } from "react";
import type { RealtimeConnectionStatus } from "@cmc/shared-types";
import { OpsConnectionBadge } from "./OpsConnectionBadge";
import { OpsHubTabs, type OpsHubTab } from "./OpsHubTabs";
import "./operations.css";

type OpsHubShellProps = {
  title: string;
  description?: string;
  tabs: OpsHubTab[];
  isAdmin?: boolean;
  connectionStatus?: RealtimeConnectionStatus;
  className?: string;
  children: ReactNode;
};

export function OpsHubShell({
  title,
  description,
  tabs,
  isAdmin = true,
  connectionStatus,
  className,
  children,
}: OpsHubShellProps) {
  return (
    <div className={className ? `ops-hub-shell ${className}` : "ops-hub-shell"}>
      <div className="ops-page-header ops-page-header--compact">
        <div className="ops-page-header-row">
          <div>
            <h1>{title}</h1>
            {description ? <p>{description}</p> : null}
          </div>
          {connectionStatus ? <OpsConnectionBadge status={connectionStatus} /> : null}
        </div>
      </div>
      <OpsHubTabs tabs={tabs} isAdmin={isAdmin} sticky />
      <div className="ops-hub-content">{children}</div>
    </div>
  );
}
