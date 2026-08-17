#!/usr/bin/env bash
# Výmena Square OAuth autorizačného kódu za access/refresh token (produkcia).
# Použitie: ./square_oauth_exchange.sh <kod_od_klientky> [redirect_uri]
#
# Kód platí len 5 minút - spusti hneď ako ho dostaneš.
# client_secret sa nikdy nedáva do chatu ani do repa - buď v .env (gitignored)
# ako SQUARE_CLIENT_SECRET=..., alebo sa vypýta tu skryto pri spustení.

set -euo pipefail

APP_ID="sq0idp-ZMgxj6tD5CW0iMEvVkr7hg"
TOKEN_URL="https://connect.squareup.com/oauth2/token"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
OUT_FILE="$SCRIPT_DIR/data/square_tokens.json"

if [ -z "${1:-}" ]; then
  echo "Použitie: $0 <autorizačný_kód> [redirect_uri]"
  exit 1
fi
CODE="$1"
REDIRECT_URI="${2:-https://valentindance.vercel.app/}"

if [ -f "$ENV_FILE" ] && grep -q '^SQUARE_CLIENT_SECRET=' "$ENV_FILE"; then
  CLIENT_SECRET="$(grep '^SQUARE_CLIENT_SECRET=' "$ENV_FILE" | cut -d= -f2-)"
else
  read -rs -p "Square client_secret: " CLIENT_SECRET
  echo
fi

mkdir -p "$(dirname "$OUT_FILE")"

RESPONSE=$(curl -s -X POST "$TOKEN_URL" \
  -H "Content-Type: application/json" \
  -H "Square-Version: 2024-08-21" \
  -d "$(cat <<JSON
{
  "client_id": "$APP_ID",
  "client_secret": "$CLIENT_SECRET",
  "code": "$CODE",
  "grant_type": "authorization_code",
  "redirect_uri": "$REDIRECT_URI"
}
JSON
)")

echo "$RESPONSE"

if echo "$RESPONSE" | grep -q '"access_token"'; then
  echo "$RESPONSE" > "$OUT_FILE"
  echo
  echo "OK - token uložený do $OUT_FILE"
else
  echo
  echo "CHYBA - pozri response vyššie (napr. sandbox/production mismatch alebo vypršaný kód)."
  echo "Predošlý platný token v $OUT_FILE (ak existoval) NEBOL prepísaný."
fi
