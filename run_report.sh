#!/bin/bash
# Valentindance (leadgen, USA) — interaktivny report (date-range picker), jeden prikaz.
# Usage: ./run_report.sh            # rozsah 2025-01 .. aktualny mesiac
#        ./run_report.sh 2026-07    # rozsah 2025-01 .. zadany koncovy mesiac
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON_BIN:-/opt/homebrew/bin/python3.11}"   # CI: PYTHON_BIN=python3
# Lokalne user ucet; v CI SM_ACCOUNT="" -> aktivny service account
export SM_ACCOUNT="${SM_ACCOUNT-analytics@signity.sk}"   # podedi pull_ppc.py (tvoj GCP projekt)
END="${1:-$(date +%Y-%m)}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT INT TERM

echo "[1/4] Tahám leady z GA4 (click_schedule_now / click_phone / click_mail)…"
"$PY" "$DIR/pull_leads.py" --out "$TMP/agg.json"

echo "[2/4] Tahám PPC + GA4 za 2025-01..$END (Google Ads, GA4 kanaly)…"
set +e
"$PY" "$DIR/pull_ppc.py" --range 2025-01 "$END" --out "$TMP/ppc.json"
PRC=$?
set -e
if [ "$PRC" -eq 3 ]; then
  echo "  GA4 kriticka chyba (prazdne channels) — NEpokracujem, nech sa nedeployuje prazdny report." >&2
  exit 3
elif [ "$PRC" -ne 0 ]; then
  echo "  (PPC ciastocne zlyhalo — dashboard s dostupnymi datami)"
fi

echo "[3/4] Tahám rezervácie zo Square…"
set +e
"$PY" "$DIR/pull_bookings.py" --out "$TMP/bookings.json"
BRC=$?
set -e
if [ "$BRC" -ne 0 ]; then
  echo "  (Square ciastocne/uplne zlyhalo — dashboard bez rezervacii, ostatne data ostavaju)"
fi

echo "[4/4] Generujem interaktivny dashboard…"
PPC_ARG=""; [ -f "$TMP/ppc.json" ] && PPC_ARG="--ppc $TMP/ppc.json"
BOOK_ARG=""; [ -f "$TMP/bookings.json" ] && BOOK_ARG="--bookings $TMP/bookings.json"
"$PY" "$DIR/build_dashboard.py" --agg "$TMP/agg.json" $PPC_ARG $BOOK_ARG --out "$DIR/report.html" --client "Valentindance"

echo "Hotovo: $DIR/report.html"
