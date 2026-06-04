import { PageShell } from "./PageShell";

export function CartPage() {
  return (
    <PageShell
      eyebrow="Customer"
      title="Cart shell"
      description="Future cart review, notes, quantity updates, and order submission will live here."
      stats={[
        { label: "Items", value: "3", detail: "Static placeholder" },
        { label: "Payment", value: "Unpaid", detail: "Matches contract wording" },
      ]}
    >
      <div className="order-card">
        <div className="order-line">
          <span>Bruschetta x1</span>
          <strong>$8.50</strong>
        </div>
        <div className="order-line">
          <span>Soup of the Day x2</span>
          <strong>$14.00</strong>
        </div>
        <div className="order-total">
          <span>Estimated total</span>
          <strong>$22.50</strong>
        </div>
      </div>
    </PageShell>
  );
}
