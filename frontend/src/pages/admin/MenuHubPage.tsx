import { AdminCategoryManager } from "../../components/admin/AdminCategoryManager";

import { AdminMenuManager } from "../../components/admin/AdminMenuManager";

import { OpsHubShell } from "../../components/operations/OpsHubShell";

import { useOpsHubTab } from "../../components/operations/OpsHubTabs";

import "../../components/operations/operations.css";
import "./menu-hub.css"; = [

  { id: "items", label: "Món" },

  { id: "categories", label: "Danh mục" },

];



export function MenuHubPage() {

  const { activeTab } = useOpsHubTab(MENU_TABS);



  return (

    <OpsHubShell
      className="ops-hub-shell--menu"
      title="Thực đơn"
      description="Quản lý món và danh mục trên cùng một màn hình."
      tabs={MENU_TABS}
      stickyTabs={false}
    >

      {activeTab === "items" ? <AdminMenuManager embedded /> : null}

      {activeTab === "categories" ? <AdminCategoryManager embedded /> : null}

    </OpsHubShell>

  );

}

