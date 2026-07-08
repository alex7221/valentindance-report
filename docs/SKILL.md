---
name: client-report-blueprint
description: >-
  Postav alebo udržuj INTERAKTÍVNY HTML DASHBOARD REPORT (živý, hostovaný na Vercel, heslo, denný
  auto-update) pre klienta PPC agentúry Signity podľa vyladenej kostry Client.sk. Klient-agnostický.
  Použi VŽDY keď operátor chce "spraviť dashboard report ako Client pre [klient]", "nasadiť/postaviť
  živý report pre [klient]", "urobiť interaktívny report pre [klient]", "dať klientovi taký report ako
  Client", "/client-report-blueprint", alebo keď zakladá nový report-dashboard projekt (kopíruje
  kostru, vymieňa zdroje dát Shoptet/WooCommerce/WP/custom, prispôsobuje KPI e-com vs leadgen, brand
  assety, deploy cez GitHub Actions). Pokrýva celý proces: výber hero obrázku/loga z webu klienta, GA4/
  Google Ads/Meta pipeline, GA4 cache pri výpadkoch, TradingView trend graf, mobile karty, Google PMAX
  shareable preview, Vercel deploy + demo pre prospektov. NIE pre mailové markdown reporty (tie sú
  per-klient skilly ako lebeddie-report/dovysky-report/fukaj-report).
---

# Dashboard report blueprint (kostra Client)

Postavenie/údržba **interaktívneho HTML dashboard reportu** pre nového klienta podľa vyladenej referencie **Client.sk**. Jeden self-contained HTML (~2 MB, dáta embednuté), hostovaný na Vercel, heslo, denný auto-update cez GitHub Actions.

## Zdroj pravdy (toto je len operatíva, detail je tam)

- **Repo kostry:** `./ (tento repo)` - skopíruj a uprav. Skripty: `parse_orders.py`, `pull_ppc.py`, `build_dashboard.py`, `run_report.sh`, `make_demo.py`, `deploy-middleware.js`, `.github/workflows/daily.yml`, `SETUP-GITHUB.md`.
- **Kompletný playbook (čítaj ako referenciu):** Obsidian nóta `(interná nóta) docs/METHODOLOGY.md` - 8 sekcií so VŠETKÝMI detailmi a gotchas. Pri akejkoľvek nejasnosti choď sem.

## Pravidlá (vždy)

- Žiadne emoji, šípky, dlhé pomlčky, kučeravé úvodzovky ani apostrofy. SK casual, vecne.
- **Credentials VŽDY do Google Secret Manager** (pracovný GCP projekt `claude-493613`), nikdy plaintext na disku, nikdy do chatu.
- **Claude má deploy dôverných klientskych dát TVRDO ZABLOKOVANÝ** (data exfiltration). Deploy s reálnymi dátami spúšťa operátor. Claude smie len **git push** a **`gh workflow run`** (to je povolené) - preto deploy ide cez GitHub Actions CI. Claude tiež **nesmie vytvárať GCP service accounty / IAM bindings / kľúče** - to robí operátor podľa `SETUP-GITHUB.md`.
- Pri editácii JS v `build_dashboard.py` template: backtick (nie apostrof) na template literály, vždy over `node --check` na vytiahnutom inline skripte.

## Postup

### 1. Discovery klienta (spýtaj sa / over)
- Platforma webu: **Shoptet** (CSV feed cp1250) / **WooCommerce** (REST API) / **WP** / **custom export**. Určuje, ktorý parser objednávok.
- **e-com vs leadgen** (kľúčové rozhodnutie, viď krok 3).
- Účty: **Google Ads** customer ID, **Meta** act_ ID, **GA4** property ID.
- Zdroj objednávok/leadov + ako sa páruje source/medium (GA4 transactionId join).
- Brand: web klienta (na hero fotku + logo), brand farba.

### 2. Setup repa
- Skopíruj kostru Client repo do nového priečinka, premenuj, `git init`.
- Secrety klienta **do Secret Managera** (feed URL, GA4 OAuth, Ads tokeny, Meta token). Account IDs nie sú tajomstvá - tie do skriptov môžu.
- Uprav `pull_ppc.py`: `GA4_PROPERTY`, `GADS_CUSTOMER`, Meta act_, secret names.
- `build_dashboard.py` beží s `--client "Brand.sk"` + `--assets-dir <dir>` (placeholdery `__BRAND__`/`__BRANDSHORT__` v title/PWA/alt sa nahradia).

### 3. e-com vs leadgen (prispôsob KPI a sekcie)
- **e-com:** KPI = obrat bez DPH, objednávky, storná, náklady na PPC, obrat z PPC (GA4), PNO (GA4). Sekcie: kanály, storná, značky treemap, top produkty/bicykle.
- **leadgen:** KPI = **leady, CPL, konverzný pomer, web formuláre** (NIE obrat/PNO/ROAS). Sekcie: kanály = leady per source/medium; **žiadne značky/produkty/storná**. Vzor leadgen logiky = klient Sportwell.
- Definuj, čo je konverzia (nákup / lead / hovor) v GA4 + Ads/Meta - mení výpočet "Obrat z PPC" resp. CPL.

### 4. Brand assety
- Hero: pekná fotka/banner z webu klienta (Shoptet CDN `cdn.myshoptet.com/...` alebo og:image), stiahni, **base64 do `assets/hero.b64`**. Tmavý gradient overlay je v template.
- Logo: do bieleho chipu, **base64 `assets/logo.b64`**. App ikona (PWA) = symbol z loga, vypĺňa ikonu, biele pozadie, generuj 180/192/512 px.
- Brand farba do `--red` CSS premennej.

### 5. KRITICKÉ ops gotchas (toto nás bolelo - drž to)
- **GA4 504/503 výpadky:** query 2024-now denne je pridlhé. Drž `ga4_run_chunked` (chunkuj **po rokoch**) + `timeout=120` + retry 5x (15/30/45/60/60s).
- **GA4 cache** (`data/ga4_cache.json`, commit-back v CI): GA4 prejde = ulož kanály+txns; GA4 padne = použi **posledné dobré GA4 + čerstvý zvyšok** a deployni. Guard: ak padne a niet cache = `exit 3` = build zlyhá = nedeployuje sa prázdny report.
- **Cron 2x denne:** ranný ~3:15 + **poobedný ~13:30** (vtedy GA4 za včerajšok dotečie - GA4 dáta sú hotové ~okolo obeda).
- **Default rozsah = tento mesiac do včera** (`DEND` = včera resp. posledný deň s dátami, nikdy neúplný dnešok). Presety končia včerajškom.
- **Cache-control `must-revalidate`** hlavičky (vercel.json) - inak mobil drží starú verziu.
- **Heslo bez prihlasovacieho mena:** Vercel Edge middleware (`deploy-middleware.js`), vlastný formulár + cookie. Heslo v `PASS` (NEpíš hodnotu nikam).
- **PWA:** manifest.json + ikony + meta tagy; middleware prepúšťa manifest/ikony bez hesla.

### 6. UX, čo treba zachovať (vyladené, nerozbi to)
- **Trend graf TradingView-style:** lineárna os (index dňa/týždňa/mesiaca v roku), čiary (tento rok plná + plocha, minulý sivá prerušovaná), **auto-fit Y na viditeľný rozsah**, granularita Mesačne/Týždenne/Denne v **dropdowne**, zoom kolieskom/pinch, ťah po osi = výška, dvojťuk reset, fullscreen modal na mobile.
- **Looker date picker** (jeden pill, dva kalendáre, presety, potvrdenie).
- **Mobile:** tabuľky = karty (`data-label`), kampane kompaktný prehľad = klik detail, storná prvých 5 + rozbaliť, skrátené hlavičky kanálov (Obj./Sess.).
- **Ad previews:** Meta shareable link; **Google PMAX shareable preview** cez `ShareablePreviewService.GenerateShareablePreviews` (`UI_PREVIEW`, `asset_group_identifier.asset_group_id`, 14-dňový link, regeneruje sa každým behom). Obrázkové assety len z ENABLED asset_group.

### 7. White-label / demo (na ukážku prospektovi)
- `make_demo.py` generuje vymyslené dáta (fiktívna značka, sezónnosť + YoY, realistické PNO ~10 %, kampaňové náklady konzistentné s KPI). Build s `--client "Demo.sk" --assets-dir assets-demo`.
- Demo = **bez password gate**, hostené ako **samostatný verejný Vercel projekt**. Reálne ad previews tam nie sú (fake dáta).

### 8. Deploy
- Privátny GitHub repo + GitHub Actions (`daily.yml`): auth cez GCP service account (`GCP_SA_KEY`), build `run_report.sh` (env `SM_ACCOUNT=""`, `PYTHON_BIN=python3`), prepare site (index.html + middleware.js + vercel.json + manifest + ikony), `vercel deploy --prod` (secrets `VERCEL_TOKEN/ORG_ID/PROJECT_ID`), commit-back `data/camp_history.json` + `data/ga4_cache.json`.
- Setup krokov A-E (SA, Vercel token, repo, secrets, test run) = runbook `SETUP-GITHUB.md` - **tieto kroky spúšťa operátor** (tvorba SA/kľúčov/secretov je mimo Claude).
- Manuálny deploy/redeploy: operátor spustí, alebo Claude `git push` + `gh workflow run daily.yml` a sleduje cez `gh run watch`.

## New-client checklist (krok po kroku)
1. [ ] Discovery: platforma, e-com/leadgen, account IDs, zdroj objednávok, brand.
2. [ ] Skopíruj kostru repo, premenuj, account IDs do skriptov.
3. [ ] Secrety klienta do Secret Managera (operátor pri SA/IAM).
4. [ ] Parser objednávok podľa platformy (rovnaký výstupný tvar agg.json).
5. [ ] KPI a sekcie podľa e-com vs leadgen.
6. [ ] Hero + logo + app ikona + brand farba do assets/.
7. [ ] Lokálny build (`run_report.sh`) + preview (mobile aj desktop), over všetky sekcie.
8. [ ] `make_demo.py` demo verzia (voliteľne, pre prospekta).
9. [ ] GitHub repo + secrets + workflow (operátor cez SETUP-GITHUB.md).
10. [ ] Test run workflow, over channel rows > 0, deploy zelený, heslo funguje.
11. [ ] Over GA4 cache + 2x denný cron + cache hlavičky.
12. [ ] Odovzdaj URL (heslo) klientovi.

## Pozn.
Pri nejasnosti vždy otvor playbook `docs/METHODOLOGY.md` (plný detail) a pozri konkrétny skript v Client repe. Tento skill je sumár flow - pravda je v repe + nóte.
