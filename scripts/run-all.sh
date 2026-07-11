#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-native}"
ENV_FILE="${2:-deploy/env/staging.env}"

if [[ "$MODE" == "--docker" ]]; then
  [[ -f "$ROOT/$ENV_FILE" ]] || { echo "Missing $ENV_FILE. Copy and fill an example env file first." >&2; exit 1; }
  exec docker compose --env-file "$ROOT/$ENV_FILE" -f "$ROOT/deploy/docker-compose.yml" up --build
fi

for file in "$ROOT/backend/.env" "$ROOT/ai/.env" "$ROOT/frontend/.env"; do
  if [[ -f "$file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$file"
    set +a
  fi
done

export Jwt__SigningKey="${Jwt__SigningKey:-${JWT_SIGNING_KEY:-}}"
export CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-http://localhost:5173;http://localhost:5174;http://localhost:5175;http://localhost:5176}"
if [[ -z "${ConnectionStrings__DefaultConnection:-}" && -n "${DB_PASSWORD:-}" ]]; then
  export ConnectionStrings__DefaultConnection="Host=${DB_HOST:-localhost};Port=${DB_PORT:-5432};Database=${DB_NAME:-restaurant_qr};Username=${DB_USERNAME:-restaurant_user};Password=${DB_PASSWORD}"
fi
[[ ${#Jwt__SigningKey} -ge 32 ]] || { echo "Set Jwt__SigningKey in backend/.env with at least 32 random characters." >&2; exit 1; }

pids=()
cleanup() {
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

(cd "$ROOT" && dotnet run --project backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj) & pids+=("$!")
(cd "$ROOT/ai" && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001) & pids+=("$!")
for portal in customer admin kitchen staff; do
  (cd "$ROOT/frontend" && npm run "dev:$portal") & pids+=("$!")
done

echo "API, AI, customer, admin, kitchen and staff servers started. Press Ctrl+C to stop."
wait -n "${pids[@]}"
echo "A server process exited; stopping the remaining processes." >&2
exit 1
