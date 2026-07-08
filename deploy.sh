#!/bin/bash
# Valentindance — build report + deploy na Vercel.
# POZOR: report obsahuje dôverné financie klienta. Spúšťaj sám, vedome.
# Odporúčanie: zapni Deployment Protection (heslo) na Vercel projekte, nech to nie je verejné.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/3] Generujem report…"
"$DIR/run_report.sh" || echo "  (build zlyhal — napr. expirovaný gcloud; nasadím posledný report.html)"

echo "[2/3] Pripravujem deploy zložku (report + heslo middleware)…"
mkdir -p "$DIR/client-report-site"
cp "$DIR/report.html" "$DIR/client-report-site/index.html"
cp "$DIR/deploy-middleware.js" "$DIR/client-report-site/middleware.js"
cp "$DIR/deploy-vercel.json" "$DIR/client-report-site/vercel.json"
cp "$DIR/deploy-manifest.json" "$DIR/client-report-site/manifest.json"
cp "$DIR/assets/icon-180.png" "$DIR/assets/icon-192.png" "$DIR/assets/icon-512.png" "$DIR/client-report-site/"

echo "[3/3] Nasadzujem na Vercel (production)…"
cd "$DIR/client-report-site"
vercel deploy --prod --yes

echo ""
echo "Hotovo. URL je vyššie. Ak ešte nie je chránené heslom:"
echo "  Vercel dashboard → projekt → Settings → Deployment Protection → zapni heslo (Pro plán)."
