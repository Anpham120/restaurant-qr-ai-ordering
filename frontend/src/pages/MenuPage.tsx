import { PageShell } from "./PageShell";

export function MenuPage() {
  const menuItems = [
    { name: "Bruschetta", detail: "Starter shell", price: "$8.50", badge: "Available" },
    { name: "Soup of the Day", detail: "Kitchen note placeholder", price: "$7.00", badge: "Available" },
    { name: "Grilled Salmon", detail: "Menu item card shell", price: "$22.00", badge: "Available" },
    { name: "Beef Burger", detail: "Unavailable state placeholder", price: "$16.50", badge: "Unavailable" },
  ];

  return (
    <PageShell
      eyebrow="Customer"
      title="Menu shell"
      description="Future menu categories, item cards, modifiers, and add-to-cart controls will live here."
      stats={[
        { label: "Categories", value: "4", detail: "Static UI groups" },
        { label: "Cart", value: "0", detail: "No persisted state yet" },
      ]}
    >
      <div className="search-shell">Search dishes, ingredients...</div>
      <div className="chip-row">
        {["All", "Starters", "Mains", "Desserts", "Drinks"].map((chip) => (
          <span className={chip === "All" ? "chip active" : "chip"} key={chip}>
            {chip}
          </span>
        ))}
      </div>
      <div className="menu-list">
        {menuItems.map((item) => (
          <article className="menu-item" key={item.name}>
            <div className="item-thumb" aria-hidden="true" />
            <div>
              <h3>{item.name}</h3>
              <p>{item.detail}</p>
              <span className={item.badge === "Available" ? "mini-badge ready" : "mini-badge muted"}>
                {item.badge}
              </span>
            </div>
            <strong>{item.price}</strong>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
