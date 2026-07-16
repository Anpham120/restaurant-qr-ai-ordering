# Refactor plan: table-session ordering and settlement

## Problem Statement

The ordering app currently mixes two different moments: sending an order round to the kitchen and settling the table. Promotion and loyalty inputs appear while sending food, payments belong to individual orders, AI can reject a valid chat when browser table data disagrees with the session, and customers lose cart context while scrolling.

The intended operation is one Table Session containing many Order Rounds and exactly one Table Invoice. Kitchen submission happens many times. Promotion, loyalty identity, payment method, and payment request happen once, only when the customer settles the table.

## Solution

Keep Ordering and Settlement as separate modules with narrow interfaces. Ordering accepts repeated order rounds under an active Table Session. Settlement builds one Table Invoice from every eligible order round in that session, validates a promotion against the aggregate subtotal, associates one loyalty phone number, and creates one payment request. Once settlement starts, the session rejects new order rounds until staff cancel the request or complete payment.

The frontend will expose a persistent cart summary while browsing, keep AI prompts and dish suggestions inside the transcript, submit order rounds without promotion or loyalty data, and open a session-level invoice modal from “Yêu cầu thanh toán”.

## Commits

1. Record the canonical Table Session, Order Round, Table Invoice, and Payment Request language. Add regression tests that describe the current ordering experience without changing runtime behavior.
2. Add the viewport-fixed cart summary with item count and current amount. Verify desktop, mobile, safe-area, and bottom-navigation spacing.
3. Make chat session identity backend-authoritative: send only the Table Session identity, derive its table on the server, and render quick prompts, errors, notices, and dish suggestions in the transcript.
4. Remove promotion and loyalty inputs from order-round submission. Keep backward-compatible request fields temporarily, but make the ordering app always submit null values.
5. Add a Table Invoice aggregate with a one-to-one relationship to Table Session. Store aggregate subtotal, discount, total, promotion, loyalty phone, status, and timestamps.
6. Generalize Payment ownership so a payment can target either a legacy Order or a Table Invoice, never both. Preserve existing order-payment records and routes during migration.
7. Add the session invoice query interface. Aggregate all non-cancelled Order Rounds in the Table Session and return line items, order-round references, subtotal, discount, and total.
8. Add the idempotent session payment-request interface. Accept payment method, optional promotion code, and optional loyalty phone. Validate the session capability, calculate promotion once against the aggregate subtotal, freeze the invoice, and create COD or VietQR payment data.
9. Reject new Order Rounds while the Table Invoice is awaiting or processing payment. Allow staff to cancel a payment request and resume ordering; close the Table Session only after confirmed payment.
10. Award loyalty points once from the paid Table Invoice total. Prevent duplicate awards on retries and payment callbacks.
11. Update staff cashier and invoice views to show one Table Invoice with all Order Rounds, one payment status, one promotion, and one loyalty member.
12. Replace the cart checkout panel with order-round confirmation only. Add a session invoice screen/modal containing aggregate items, promotion entry, loyalty phone, payment method, and final total.
13. Add integration tests for multiple order rounds, aggregate promotion, idempotent payment requests, rejected post-settlement ordering, payment cancellation, successful COD/VietQR confirmation, and single loyalty award.
14. Add browser smoke coverage for persistent cart, AI transcript suggestions, repeated kitchen submissions, session invoice review, promotion application, and payment request.
15. Remove legacy per-order promotion/loyalty UI and compatibility code after production verification confirms no active client depends on it.

## Decision Document

- A Table Session represents one dine-in visit at one table.
- A Table Session can contain many Order Rounds.
- An Order Round sends food to the kitchen and is not a checkout operation.
- A Table Session has at most one active Table Invoice.
- Promotion and loyalty identity belong to the Table Invoice, not an Order Round.
- Promotion is calculated once against the aggregate eligible subtotal.
- Payment is requested and confirmed against the Table Invoice.
- Starting settlement freezes additional ordering to prevent the invoice changing during payment.
- Staff may cancel an unpaid request to reopen ordering.
- Confirmed payment closes the Table Session and awards loyalty once.
- Table identity for AI is derived from the validated Table Session, not trusted from browser state.
- Existing order-level payment data remains readable during migration.

## Testing Decisions

- Tests assert externally visible domain behavior rather than private implementation details.
- Ordering tests cover repeated order rounds and the settlement freeze.
- Settlement tests cover aggregate totals, promotion validity, idempotency, and payment state transitions.
- Loyalty tests prove exactly-once awarding after payment confirmation.
- Frontend tests cover persistent cart visibility, transcript-contained AI suggestions, order-only cart submission, and invoice-only promotion/loyalty fields.
- Existing order lifecycle and payment lifecycle integration tests provide the prior-art structure.
- Production release requires frontend tests/build, backend tests/build, Docker Compose validation, CI/security checks, and a browser smoke test.

## Out of Scope

- Split bills by guest or item.
- Multiple simultaneous payment methods for one invoice.
- Deposits, tips, refunds by individual dish, and partial settlement.
- Pickup/delivery checkout changes.
- Reopening a Table Session after confirmed payment.

## Further Notes

The rollout remains backward compatible until the session invoice path has passed production smoke checks. Every implementation slice must be committed, merged into `main`, and deployed before the next slice is considered complete.
