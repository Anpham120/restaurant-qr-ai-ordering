#!/usr/bin/env bash
set -euo pipefail

: "${DEPLOY_ENV:?DEPLOY_ENV is required}"
: "${FRONTEND_SERVER_NAMES:?FRONTEND_SERVER_NAMES is required}"
: "${API_SERVER_NAME:?API_SERVER_NAME is required}"
: "${AI_INTERNAL_TOKEN:?AI_INTERNAL_TOKEN is required}"

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
curl --fail --show-error --silent --retry 10 --retry-delay 5 --retry-all-errors "$ai_ready_url"

echo "Running protected AI smoke request"
curl --fail --show-error --silent --retry 2 --retry-delay 2 --retry-all-errors \
  -H "Authorization: Bearer ${AI_INTERNAL_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"message":"Xin chào"}' \
  "$ai_chat_url" >/dev/null

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
- Protected AI smoke: PASS
- Checked at UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Result: PASS

## Compose Status

\`\`\`json
${compose_status}
\`\`\`
EOF

echo "Health check passed for ${DEPLOY_ENV}"
