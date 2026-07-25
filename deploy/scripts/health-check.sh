#!/usr/bin/env bash
set -euo pipefail

: "${DEPLOY_ENV:?DEPLOY_ENV is required}"
: "${FRONTEND_SERVER_NAMES:?FRONTEND_SERVER_NAMES is required}"
: "${API_SERVER_NAME:?API_SERVER_NAME is required}"
: "${AI_INTERNAL_TOKEN:?AI_INTERNAL_TOKEN is required}"
: "${AI_PIPELINE_PROFILE:?AI_PIPELINE_PROFILE is required}"
: "${LLM_MODEL:?LLM_MODEL is required}"

primary_frontend_domain="$(printf '%s\n' "$FRONTEND_SERVER_NAMES" | awk '{print $1}')"
frontend_url="${FRONTEND_HEALTH_URL:-https://${primary_frontend_domain}/}"
api_health_url="${API_HEALTH_URL:-https://${API_SERVER_NAME}/api/health}"
api_ready_url="${API_READY_URL:-https://${API_SERVER_NAME}/health/ready}"
ai_ready_url="${AI_READY_URL:-http://127.0.0.1:${AI_SERVICE_PORT:-8001}/ready}"
ai_chat_url="${AI_CHAT_URL:-http://127.0.0.1:${AI_SERVICE_PORT:-8001}/v1/chat}"

echo "Checking frontend: ${frontend_url}"
curl --fail --show-error --silent --retry 10 --retry-delay 5 --retry-all-errors "$frontend_url" >/dev/null

echo "Checking API health: ${api_health_url}"
curl --fail --show-error --silent --retry 10 --retry-delay 5 --retry-all-errors "$api_health_url"

echo "Checking API readiness (database and AI dependency): ${api_ready_url}"
curl --fail --show-error --silent --retry 10 --retry-delay 5 --retry-all-errors "$api_ready_url"

echo "Checking AI readiness: ${ai_ready_url}"
probe_dir="$(mktemp -d)"
trap 'rm -rf "$probe_dir"' EXIT
ready_payload="${probe_dir}/ready.json"
curl --fail --show-error --silent --retry 10 --retry-delay 5 --retry-all-errors \
  "$ai_ready_url" > "$ready_payload"
python3 - "$ready_payload" "$AI_PIPELINE_PROFILE" "$LLM_MODEL" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
expected_profile, expected_model = sys.argv[2], sys.argv[3]
assert payload.get("ready") is True, payload
assert payload.get("pipeline_profile") == expected_profile, payload
assert payload.get("model") == expected_model, payload
PY

echo "Running protected basic AI smoke request"
curl --fail --show-error --silent --retry 2 --retry-delay 2 --retry-all-errors \
  -H "Authorization: Bearer ${AI_INTERNAL_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"message":"Xin chào"}' \
  "$ai_chat_url" >/dev/null

menu_dataset="/opt/cmc-restaurant/${DEPLOY_ENV}/repo/backend/data/menu-dataset.json"
run_semantic_probe() {
  local probe_name="$1"
  local probe_message="$2"
  local request_file="${probe_dir}/${probe_name}-request.json"
  local response_file="${probe_dir}/${probe_name}-response.json"

  python3 - "$menu_dataset" "$request_file" "$probe_message" "$AI_PIPELINE_PROFILE" <<'PY'
import json
import sys

source, target, message, profile = sys.argv[1:5]
raw = json.load(open(source, encoding="utf-8-sig"))
menu_items = [
    {
        "id": item["id"],
        "name": item["name"],
        "description": item.get("description") or "",
        "category_id": item.get("categoryId") or "",
        "category_name": item.get("categoryName") or "",
        "price_vnd": item.get("price"),
        "tags": item.get("tags") or [],
        "is_available": bool(item.get("isAvailable", True)),
    }
    for item in raw["items"]
]
payload = {
    "contract_version": "v2",
    "message": message,
    "session_id": f"deploy-smoke-{profile}",
    "pipeline_profile": profile,
    "session_state": {
        "facts": [],
        "constraints": {},
        "memory_version": "v2",
        "conversation_frame": {"turn_sequence": 0},
    },
    "live_context": {
        "catalog_version": "deploy-smoke-menu",
        "menu_items": menu_items,
        "table_code": "SMOKE",
    },
}
with open(target, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False)
PY

  curl --fail --show-error --silent --retry 2 --retry-delay 2 --retry-all-errors \
    -H "Authorization: Bearer ${AI_INTERNAL_TOKEN}" \
    -H "Content-Type: application/json" \
    --data-binary "@${request_file}" \
    "$ai_chat_url" > "$response_file"

  python3 - "$response_file" "$AI_PIPELINE_PROFILE" "$LLM_MODEL" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
expected_profile, expected_model = sys.argv[2], sys.argv[3]
content = str(payload.get("content") or "").casefold()
assert payload.get("pipeline_profile") == expected_profile, payload
assert payload.get("model") == expected_model, payload
assert payload.get("provider_available") is True, payload
assert "mình chưa đủ bằng chứng" not in content, payload
assert payload.get("verifier_result") != "failed", payload
assert payload.get("resolved_menu_item_ids"), payload
assert payload.get("evidence"), payload
assert all(bool(claim.get("verified")) for claim in payload.get("claims") or []), payload
PY
}

echo "Running protected semantic AI smoke probes"
run_semantic_probe "pho-list" "Nhà hàng mình có những món phở gì nhỉ?"
run_semantic_probe "pho-recommend" "Gợi ý cho mình món phở tại nhà hàng đi"
run_semantic_probe "nhau" "Mình có món nhậu không?"

report_dir="/opt/cmc-restaurant/${DEPLOY_ENV}/reports"
mkdir -p "$report_dir"
compose_file="/opt/cmc-restaurant/${DEPLOY_ENV}/repo/deploy/docker-compose.yml"
compose_status="not checked"
if [ -f "$compose_file" ] && [ -n "${COMPOSE_PROJECT_NAME:-}" ]; then
  compose_status="$(docker compose --env-file "/opt/cmc-restaurant/${DEPLOY_ENV}/.env" -f "$compose_file" -p "$COMPOSE_PROJECT_NAME" ps --format json 2>/dev/null || true)"
fi

cat > "${report_dir}/last-deployment.md" <<EOF
# Deployment Report

- Environment: ${DEPLOY_ENV}
- Frontend URL: ${frontend_url}
- API health URL: ${api_health_url}
- API readiness URL: ${api_ready_url}
- AI readiness URL: ${ai_ready_url}
- Protected semantic AI smoke (3 production cases): PASS
- Pipeline profile: ${AI_PIPELINE_PROFILE}
- LLM model: ${LLM_MODEL}
- Checked at UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Result: PASS

## Compose Status

\`\`\`json
${compose_status}
\`\`\`
EOF

echo "Health check passed for ${DEPLOY_ENV}"
