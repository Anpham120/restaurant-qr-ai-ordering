#!/usr/bin/env bash
set -euo pipefail

if [ "${ENABLE_CERTBOT:-true}" != "true" ]; then
  echo "Certbot disabled by ENABLE_CERTBOT=false"
  exit 0
fi

: "${FRONTEND_SERVER_NAMES:?FRONTEND_SERVER_NAMES is required}"
: "${API_SERVER_NAME:?API_SERVER_NAME is required}"

domains=()
for domain in $FRONTEND_SERVER_NAMES; do
  domains+=("-d" "$domain")
done
domains+=("-d" "$API_SERVER_NAME")

email_args=()
if [ -n "${CERTBOT_EMAIL:-}" ]; then
  email_args=(--email "$CERTBOT_EMAIL")
else
  email_args=(--register-unsafely-without-email)
fi

certbot --nginx \
  --non-interactive \
  --agree-tos \
  --expand \
  --redirect \
  "${email_args[@]}" \
  "${domains[@]}"
