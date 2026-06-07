#!/usr/bin/env bash
set -euo pipefail

: "${DEPLOY_ENV:?DEPLOY_ENV is required}"
: "${FRONTEND_SERVER_NAMES:?FRONTEND_SERVER_NAMES is required}"
: "${API_SERVER_NAME:?API_SERVER_NAME is required}"

primary_frontend_domain="$(printf '%s\n' "$FRONTEND_SERVER_NAMES" | awk '{print $1}')"
frontend_url="${FRONTEND_HEALTH_URL:-https://${primary_frontend_domain}/}"
api_health_url="${API_HEALTH_URL:-https://${API_SERVER_NAME}/api/health}"

echo "Checking frontend: ${frontend_url}"
curl --fail --show-error --silent --retry 10 --retry-delay 5 "$frontend_url" >/dev/null

echo "Checking API health: ${api_health_url}"
curl --fail --show-error --silent --retry 10 --retry-delay 5 "$api_health_url"

report_dir="/opt/cmc-restaurant/${DEPLOY_ENV}/reports"
mkdir -p "$report_dir"
cat > "${report_dir}/last-deployment.md" <<EOF
# Deployment Report

- Environment: ${DEPLOY_ENV}
- Frontend URL: ${frontend_url}
- API health URL: ${api_health_url}
- Checked at UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- Result: PASS
EOF

echo "Health check passed for ${DEPLOY_ENV}"
