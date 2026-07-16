/**
 * Playwright-oriented E2E checklist for AI pipeline v2.
 * Automate against staging when credentials/env are available.
 *
 * Scenarios:
 * 1. Open table session → AI tab → send message → suggestion cards appear
 * 2. Confirm card → cart quantity increases (server cart) → ledger status confirmed after refresh
 * 3. Dismiss card → refresh → card remains dismissed
 * 4. Ask for more suggestions → no duplicate menuItemIds from prior turns
 * 5. Navigate to menu then back to AI → history preserved
 * 6. Kitchen marks item unavailable → card Confirm disabled via menu.availabilityChanged
 * 7. Close table session → chat history gone for new session
 * 8. Rate-limit: rapid 12 messages → 429
 * 9. Assistance button → staff ops receives assistance.requested
 * 10. Feedback thumbs → admin /api/admin/chat/feedback lists entry
 */
export const AI_E2E_SCENARIOS = [
  "session-memory-restore",
  "no-duplicate-recommendations",
  "server-cart-multi-device",
  "menu-availability-live",
  "staff-handoff",
  "feedback-loop",
] as const;
