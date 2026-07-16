type SessionInvoiceSummary = {
  subtotalAmount: number;
  orderRounds: readonly unknown[];
};

type CartSummaryLine = {
  quantity: number;
  unitPrice: number;
};

export type CartSessionSummary = {
  orderedSubtotal: number;
  cartSubtotal: number;
  projectedTotal: number;
  orderRoundCount: number;
  selectedQuantity: number;
};

export function buildCartSessionSummary(
  invoice: SessionInvoiceSummary | null,
  cartLines: readonly CartSummaryLine[],
): CartSessionSummary {
  const cartSubtotal = cartLines.reduce(
    (total, line) => total + line.quantity * line.unitPrice,
    0,
  );
  const selectedQuantity = cartLines.reduce(
    (total, line) => total + line.quantity,
    0,
  );
  const orderedSubtotal = invoice?.subtotalAmount ?? 0;

  return {
    orderedSubtotal,
    cartSubtotal,
    projectedTotal: orderedSubtotal + cartSubtotal,
    orderRoundCount: invoice?.orderRounds.length ?? 0,
    selectedQuantity,
  };
}
