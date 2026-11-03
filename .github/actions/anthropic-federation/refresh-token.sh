#!/usr/bin/env bash
# Writes a fresh GitHub OIDC token (audience https://api.anthropic.com) to $1 every 2 minutes.
set -u
out="$1"
while true; do
  if curl -sSf -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
      "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=https://api.anthropic.com" \
      | jq -r .value > "$out.tmp" && [ -s "$out.tmp" ]; then
    mv "$out.tmp" "$out"
  else
    echo "$(date -u +%T) token fetch failed; keeping the previous token"
  fi
  sleep 120
done
