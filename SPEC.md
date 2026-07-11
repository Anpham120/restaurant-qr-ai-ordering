# SPEC

§G

G1: chat theo table session bền qua refresh/browser exit; full history + compact AI memory; latency tối thiểu.

§C

C1: PostgreSQL chat tables = source truth; browser storage chỉ giữ opaque chat session id.
C2: table session open → restore; close/expire → chat history + memory xóa cho khách kế.
C3: memory ! bounded; ⊥ extra LLM call chỉ để nhớ.
C4: current user message → downstream prompt đúng 1 lần.
C5: menu/price/availability canonical backend validation giữ nguyên.
C6: preserve unrelated notebook changes + assets/.

§I

I.session: POST /api/chat/sessions → 200 {chatSessionId,createdAt,updatedAt,reused,messages[]}
I.message: POST /api/chat/sessions/{chatSessionId}/messages → 200 {message,suggestedCartActions,guardrailFlags,diagnostics}
I.history: GET /api/chat/sessions/{chatSessionId}/messages → 200 ordered full history
I.storage: cmc-chat-session:<tableSessionId> → localStorage; anonymous → sessionStorage
I.ai: backend ChatAiRequest → Python /v1/chat {message,history,session_memory,menu_items,table_code}

§V

V1: ∀ open table session → exactly same active chat session restored after refresh/browser exit.
V2: ∀ persisted chat turn → ordered full history restored from DB; ⊥ browser-only message truth.
V3: table session close/expire → linked chat session/messages/memory unavailable.
V4: AI context → last 6 turns + compact older user memory derived from persisted history; current user message exactly once.
V5: compact memory ≤ 1200 chars & ≤ 8 older unique user turns; ⊥ extra provider call.
V6: restore path ≤ 1 chat HTTP round trip: stored id → history GET; no stored id → create/restore POST incl history.
V7: menu context cache TTL ≤ 2s; suggested action still canonicalized from cached typed menu snapshot + order backend validation.
V8: AI HTTP uses pooled client, response-header streaming, bounded timeout, safe fallback.
V9: frontend + backend + AI tests cover persistence, restore, memory injection, stale stored id, close cleanup.
V10: production retriever select only by dev nDCG@10 + latency tiebreak; frozen test ! select.

§T

id|status|task|cites
T1|x|durable table-chat restore + history in create response|V1,V2,V3,V6,I.session,I.history,I.storage
T2|x|bounded persistent session memory → AI prompt|V2,V4,V5,I.message,I.ai
T3|x|safe latency cuts: menu cache + streamed AI response|V7,V8,I.ai
T4|x|run targeted/full verification + completion audit|V1,V2,V3,V4,V5,V6,V7,V8,V9
T5|x|select retriever on dev; test frozen|V10

§B

id|date|cause|fix
B1|2026-07-11|frontend deps absent; vitest binary missing|npm install
B2|2026-07-11|ChatMenuItem.Tags IList incompatible with ChatMenuItemContext|materialize ToList()
B3|2026-07-11|chat integration fixture skipped canonical menu/table seed|SeedDatabaseAsync
B4|2026-07-11|chat action test expected stale m_001 price 65000|use canonical 45000
B5|2026-07-11|E2E fixtures expected stale 200/201 API statuses|align current contracts
B6|2026-07-11|retriever winner selected on frozen test|V10
