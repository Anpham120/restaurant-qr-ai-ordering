#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  DEPLOY_ENV
  SSH_HOST
  SSH_USER
  SSH_KEY
  COMPOSE_PROJECT_NAME
  FRONTEND_PORT
  BACKEND_PORT
  FRONTEND_SERVER_NAMES
  API_SERVER_NAME
  PUBLIC_API_BASE_URL
  JWT_SIGNING_KEY
  AI_BASE_URL
  AI_MODEL
  AI_API_KEY
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name:-}" ]; then
    echo "Missing required variable: ${var_name}" >&2
    exit 1
  fi
done

root_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

key_file="${work_dir}/deploy_key"
known_hosts_file="${work_dir}/known_hosts"
tarball="${work_dir}/release.tgz"

printf '%s\n' "$SSH_KEY" > "$key_file"
chmod 600 "$key_file"
ssh-keyscan -H "$SSH_HOST" > "$known_hosts_file" 2>/dev/null

tar -C "$root_dir" \
  --exclude='.git' \
  --exclude='.playwright-cli' \
  --exclude='tmp' \
  --exclude='**/node_modules' \
  --exclude='**/bin' \
  --exclude='**/obj' \
  --exclude='frontend/dist' \
  -czf "$tarball" .

remote_root="/opt/cmc-restaurant/${DEPLOY_ENV}"
ssh_base=(ssh -i "$key_file" -o UserKnownHostsFile="$known_hosts_file" -o StrictHostKeyChecking=yes "${SSH_USER}@${SSH_HOST}")
scp_base=(scp -i "$key_file" -o UserKnownHostsFile="$known_hosts_file" -o StrictHostKeyChecking=yes)

"${ssh_base[@]}" "mkdir -p '${remote_root}' '${remote_root}/reports' '${remote_root}/backups'"
"${scp_base[@]}" "$tarball" "${SSH_USER}@${SSH_HOST}:${remote_root}/release.tgz"

env_quote() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//\$/\\$}"
  value="${value//\`/\\\`}"
  printf '"%s"' "$value"
}

env_file="${work_dir}/deploy.env"
cat > "$env_file" <<EOF
DEPLOY_ENV=$(env_quote "$DEPLOY_ENV")
COMPOSE_PROJECT_NAME=$(env_quote "$COMPOSE_PROJECT_NAME")
FRONTEND_PORT=$(env_quote "$FRONTEND_PORT")
BACKEND_PORT=$(env_quote "$BACKEND_PORT")
FRONTEND_SERVER_NAMES=$(env_quote "$FRONTEND_SERVER_NAMES")
API_SERVER_NAME=$(env_quote "$API_SERVER_NAME")
PUBLIC_API_BASE_URL=$(env_quote "$PUBLIC_API_BASE_URL")
ASPNETCORE_ENVIRONMENT=$(env_quote "${ASPNETCORE_ENVIRONMENT:-Production}")
JWT_SIGNING_KEY=$(env_quote "$JWT_SIGNING_KEY")
AI_PROVIDER=$(env_quote "${AI_PROVIDER:-9router}")
AI_BASE_URL=$(env_quote "$AI_BASE_URL")
AI_API_KEY=$(env_quote "$AI_API_KEY")
AI_MODEL=$(env_quote "$AI_MODEL")
AI_TIMEOUT_SECONDS=$(env_quote "${AI_TIMEOUT_SECONDS:-60}")
AI_MAX_RETRY=$(env_quote "${AI_MAX_RETRY:-1}")
VITE_USE_MOCK_CHAT=$(env_quote "${VITE_USE_MOCK_CHAT:-false}")
ENABLE_CERTBOT=$(env_quote "${ENABLE_CERTBOT:-true}")
CERTBOT_EMAIL=$(env_quote "${CERTBOT_EMAIL:-}")
EOF

"${scp_base[@]}" "$env_file" "${SSH_USER}@${SSH_HOST}:${remote_root}/.env"

"${ssh_base[@]}" "cd '${remote_root}' && \
  chmod 600 .env && \
  rm -rf repo.previous && \
  if [ -d repo ]; then mv repo repo.previous; fi && \
  mkdir -p repo && \
  tar -xzf release.tgz -C repo && \
  rm -f release.tgz && \
  set -a && . ./.env && set +a && \
  docker compose --env-file .env -f repo/deploy/docker-compose.yml -p '${COMPOSE_PROJECT_NAME}' up -d --build --remove-orphans && \
  bash repo/deploy/scripts/write-nginx-config.sh && \
  bash repo/deploy/scripts/issue-certbot.sh && \
  bash repo/deploy/scripts/health-check.sh"
