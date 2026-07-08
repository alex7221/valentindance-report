# Klientsky výkonnostný report - dashboard kostra

Znovupoužiteľná kostra na **interaktívny HTML dashboard report** pre PPC klientov. Jeden self-contained HTML súbor (~2 MB, dáta embednuté, žiadny backend), hostovaný na Verceli, chránený heslom, s denným auto-updatom cez GitHub Actions.

Referenčná implementácia (vyladená do detailu): e-shop klient na Shoptete. Táto kostra je **klient-agnostická** - vymeníš zdroje dát, účty a branding a máš report pre svojho klienta (e-com aj leadgen).

> Plný playbook so všetkými detailmi a gotchas: **`docs/METHODOLOGY.md`**. Tu je rýchly štart.

> **Leadgen klient** (fyzio, služby, B2B dopyty - leady namiesto objednávok)? Súbory v roote sú e-com. Leadgen obdoba (zdroj = Google Sheet leadov, KPI = leady/CPL, GA4 `generate_lead`) je v **`leadgen/`** - viď `leadgen/README.md`. Referencia: Sportwell.

> **Škáluješ na veľa klientov?** Reporty vedia čítať z **BigQuery** namiesto ťahania z API pri každom builde (rýchlejšie, bez rate limitov, dáta na jednom mieste, ~$0/mes). Hotové súbory na zapnutie BQ mode sú v **`bigquery/`** (`export_from_bq.py`, `bootstrap.sh`, `run_report.sh`, `daily.bq.yml` + návod `bigquery/README.md`). Architektúra a pozadie: **`docs/BIGQUERY.md`**.

## Čo to vie

- KPI karty (obrat, objednávky, storná, PPC náklady, obrat z PPC, PNO) s prepínačom YoY/MoM.
- Looker-style date picker (presety, default = tento mesiac do včera).
- Trend graf v štýle TradingView (lineárna os, čiary, auto-fit zvislej osi, granularita mesačne/týždenne/denne, zoom/pan).
- Tabuľka kanálov (source/medium z GA4), storná so source/medium, treemap značiek, top produkty.
- Záložka PPC kampane: budget summary, sortovateľné stĺpce, na mobile kompaktný prehľad s rozklikom na detail, náhľady reklám (Meta shareable preview + Google PMAX shareable preview cez ShareablePreviewService).
- Plne responzívne (tabuľky sa na mobile menia na karty), PWA (pridanie na plochu).

## Stack

- **Python 3.11+**: `parse_orders.py` (objednávky), `pull_ppc.py` (GA4 + Google Ads + Meta cez API), `build_dashboard.py` (generuje HTML).
- **Bash**: `run_report.sh` (jeden príkaz cez celý pipeline).
- **Node** (len `node --check` na validáciu inline JS) - voliteľné.
- Deploy: **Vercel** + **GitHub Actions** (denný cron).

## Rýchly štart - pozri demo (fake dáta, žiadne credentials)

Najrýchlejšie ako uvidíš, ako report vyzerá, je demo s vymyslenými dátami:

```bash
pip install google-analytics-data google-ads requests pillow
python3 make_demo.py
python3 build_dashboard.py --agg /tmp/demo_agg.json --ppc /tmp/demo_ppc.json \
  --client "Demo.sk" --assets-dir assets-demo --out demo_report.html
open demo_report.html
```

Demo je aj návod, ako vyzerajú vstupné dáta (`/tmp/demo_agg.json`, `/tmp/demo_ppc.json`) - keď robíš reálneho klienta, tvoj pipeline musí vyprodukovať rovnaký tvar.

## Reálny klient - kroky

1. **Discovery:** platforma webu (Shoptet / WooCommerce / WP / custom), e-com vs leadgen, account IDs (Google Ads, Meta act_, GA4 property), zdroj objednávok/leadov, brand (logo + hero z webu klienta).
2. **Credentials do Secret Managera** (nikdy plaintext do repa). Secret names sú v `pull_ppc.py` a `run_report.sh` - prispôsob.
3. **Account IDs** v `pull_ppc.py` (`GA4_PROPERTY`, `GADS_CUSTOMER`, `GADS_MCC`, Meta act_) sú placeholdery - nahraď reálnymi. ocid pre Google preview link tiež.
4. **Parser objednávok** podľa platformy. `parse_orders.py` je pre Shoptet CSV (cp1250, `;`). Pre WooCommerce/WP napíš vlastný, ale drž **rovnaký výstupný tvar** `agg.json`.
5. **KPI a sekcie** podľa e-com vs leadgen (viď `docs/METHODOLOGY.md`, sekcia 3 a 8). Leadgen = leady/CPL namiesto obrat/PNO, žiadne značky/produkty.
6. **Branding:** hero fotku + logo z webu klienta do `assets/` (base64; `assets/*.b64` sú teraz placeholdery). Brand farba v CSS premennej `--red` v `build_dashboard.py`.
7. **Heslo** na report v `deploy-middleware.js` (`PASS`) - zmeň (placeholder `CHANGE-ME-PASSWORD`).
8. **Lokálny build:** `./run_report.sh` a otvor výsledný HTML. Skontroluj desktop aj mobile.
9. **Deploy:** podľa `SETUP-GITHUB.md` (GCP service account, Vercel projekt, GitHub secrets, cron). Denný auto-update beží potom sám.

## Dôležité (ops gotchas - bez nich to v cloude padá)

Detail v `docs/METHODOLOGY.md`, sekcia 5. V skratke:
- GA4 query chunkuj **po rokoch** + retry + **cache** (`data/ga4_cache.json`) pri výpadkoch + guard, ktorý nenasadí prázdny report.
- Cron **2x denne** (ranný + poobedný, keď GA4 za včerajšok dotečie).
- Cache-control `must-revalidate` hlavičky (`deploy-vercel.json`).
- V CI použi **GCP service account** (user token expiruje).

## Bezpečnosť

- **Reálne klientske dáta** (`data/*.json`, PII CSV, reálne account IDs, heslá) **NIKDY necommituj** do zdieľaného repa. `.gitignore` to chráni; `data/` v template je prázdne.
- Credentials výhradne v Secret Manageri.

## Štruktúra

```
parse_orders.py      objednávky/leady -> agg.json
pull_ppc.py          GA4 + Google Ads + Meta -> ppc.json
build_dashboard.py   agg + ppc -> jeden HTML (--client, --assets-dir)
run_report.sh        celý pipeline jedným príkazom
make_demo.py         vymyslené dáta na demo/ukážku
deploy-middleware.js Vercel heslo (Edge middleware, bez prihlasovacieho mena)
deploy-*.json        manifest (PWA) + cache hlavičky
.github/workflows/   denný build + deploy
SETUP-GITHUB.md      runbook na nasadenie (SA, Vercel, secrets)
docs/METHODOLOGY.md  plný playbook (architektúra, UX, gotchas, per-klient variácie)
docs/SKILL.md        Claude Code skill (ak používaš Claude Code; skopíruj do ~/.claude/skills/)
assets/              branding (placeholder - nahraď klientskym)
assets-demo/         branding pre demo
```
