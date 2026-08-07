# AI no-touch boundary

Refactors to restaurant operations **must not** modify AI/RAG implementation or contracts unless explicitly approved.

## Frozen directories

| Path | Scope |
|------|--------|
| `ai/` | FastAPI service, RAG pipeline, knowledge base, evaluation, tests |
| `docs/ai/` | AI operations and ADR documentation |
| `ai/contracts/ai-chat-v1.schema.json` | Chat request/response schema |

## Integration surface (read-only during ops refactor)

| Layer | File | Contract |
|-------|------|----------|
| Frontend | `frontend/src/services/chatService.ts` | `/chat/sessions`, messages, stream, recommendations, feedback, assistance |
| Backend adapter | `backend/src/RestaurantQrAiOrdering.Api/Chat/ChatAiProvider.cs` | `POST {AI_SERVICE_URL}/v1/chat`, `/v1/chat/stream` |
| Backend API | `backend/src/RestaurantQrAiOrdering.Api/Chat/ChatEndpoints.cs` | Public chat routes bound to table session |
| Ordering UI | `frontend/apps/ordering-web` route `ai` | AI launcher entry only; layout may change, routes must remain |

## Allowed changes outside AI

- Preserve chat API paths and payload shapes consumed by `chatService.ts`
- Keep ordering app route `/table-session/:id/ai` reachable
- Do not rename or remove chat HTTP endpoints without coordinated AI + frontend updates

## Regression gates

- `frontend/src/ordering/aiContractBoundary.test.ts`
- `backend/tests/RestaurantQrAiOrdering.Api.Tests/AiContractBoundaryTests.cs`
- CI `ai-service-build` job unchanged
