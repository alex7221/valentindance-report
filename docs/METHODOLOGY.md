---
type: tema
---
# Report dashboard blueprint

Kostra pre **interaktívny HTML dashboard report** pre klientov Signity. Iný typ reportu než mailové markdown reporty (tie viď Reporting) - toto je **živý hostovaný dashboard** (Vercel, heslo, denný auto-update), nie príloha do mailu.

Referenčná implementácia (vyladená do detailu): **Client** report. Tento dokument je playbook, ako to postaviť pre ďalších klientov (rôzne zdroje: Shoptet/WooCommerce/WP/custom; e-com vs leadgen).

Repo kostry (Client): `./ (tento repo)` (privátny GitHub `YOUR-ORG/client-report`). Skopíruj a uprav.

---

## 1. Architektúra a pipeline

Tri Python skripty + jeden bash, výstup = **jeden self-contained HTML** (~2 MB, dáta embednuté priamo v ňom, žiadny backend).

```
run_report.sh  (jeden príkaz, koncový mesiac voliteľný)
  1. stiahne objednávky (Shoptet feed URL zo Secret Managera) do mktemp dir
  2. parse_orders.py  = /tmp/agg.json   (per-mesačné/týždenné agregáty, orders, lines, cancelled)
  3. pull_ppc.py --range 2024-01 <end>  = /tmp/ppc.json  (GA4 + Google Ads + Meta priamo cez API)
  4. build_dashboard.py --agg --ppc --out client_report.html
PII CSV žije len v mktemp, po behu sa maže (trap EXIT).
```

- **parse_orders.py**: Shoptet CSV je **cp1250, `;`-delimited**, 1 riadok = 1 položka objednávky. Kľúčové polia: `code, date, statusName, totalPriceWithoutVat, itemName, itemCode, itemManufacturer (=značka), itemAmount, itemTotalPriceWithoutVat, orderItemType`. **Storná gotcha:** pri storne Shoptet **vynuluje hlavičkové sumy** - hodnotu treba zrekonštruovať zo súčtu položiek. Obrat = nestornované, `totalPriceWithoutVat` deduplikované per `code`. Výstup: `monthly`/`weekly` agregáty (od 2024-01 kvôli YoY), `orders` [{d,v,c}], `lines` [{d,b,nm,q,r,bk}], `cancelled` [{code,date,net,country}].
- **pull_ppc.py**: ťahá GA4 (Data API), Google Ads (google-ads lib), Meta (Graph API) **priamo cez API** (netreba bežiace MCP servery). Výstup: `daily` PPC, `txns` (GA4 transactionId = source/medium), `channels` (denné sessions/obj/revenue per source/medium), `campaigns`, `camp_daily`, `camp_window`, `budgets`, `rsa`, `gimgs`, `gprev`, `creatives`.
- **build_dashboard.py**: vezme agg+ppc JSON, vloží do HTML template (`TEMPLATE.replace("/*__DATA__*/", json)`), vypíše HTML. Pozor pri editácii JS v template: uzatváraj template literály backtickom, over `node --check` na vytiahnutom inline skripte.

**Credentials VŽDY v Google Secret Manager** (pracovný GCP projekt `claude-493613`), nikdy plaintext. Secret names (Client): `ORDERS_FEED_URL` (obsahuje hash+PII), `GA4_CLIENT_ID/SECRET/REFRESH_TOKEN`, `ADS_DEVELOPER_TOKEN/CLIENT_ID/CLIENT_SECRET/GOOGLE_ADS_REFRESH_TOKEN`, `META_ACCESS_TOKEN`. Viď Bezpečnosť.

---

## 2. Zdroje dát a ako ich vymeniť per klient

| Vrstva | Client (referencia) | Iný klient |
|---|---|---|
| Objednávky/leady | Shoptet CSV export feed | WooCommerce REST API, WP custom export, CSV, alebo GA4 ecommerce. Pre **leadgen** = "objednávky" sú **leady** (z formulára / CRM / Sheetu). |
| PPC | Google Ads API (`1234567890`) + Meta (`act_100000000000000`) | swap account IDs |
| GA4 | property `123456789`, channels + txns | swap property ID |

- **source/medium per objednávka** = **GA4 join**: order code = GA4 `transactionId`, párované na `sessionSourceMedium`. GA4 pokrýva ~60 % objednávok (zvyšok consent/tracking gap). Pre WP/custom rovnaký princíp ak posielajú transactionId do GA4.
- Pri **leadgen** klientovi (napr. Sportwell): KPI nie obrat/PNO/ROAS ale **leady, CPL, konverzný pomer, web formuláre**; "kanály" tabuľka = leady per source/medium; žiadne značky/produkty.

---

## 3. Report sekcie a UX rozhodnutia (jadro - toto bolo najviac ladené)

**Hero header.** Full-width sticky header s fotkou z webu klienta. Výber obrázku: vezmi peknú fotku/banner z CDN klienta (Shoptet: `cdn.myshoptet.com/usr/...`, alebo og:image), stiahni, base64 do `assets/hero.b64`. Tmavý gradient overlay (`linear-gradient(90deg, rgba(10,12,14,.86), .45 55%, .28)`) aby text/logo boli čitateľné. Logo do bieleho chipu (base64 `assets/logo.b64`); ak treba len symbol (napr. app ikona), vyrež časť loga. **Logo je klikateľné = `goHome()`** (Prehľad tab + default rozsah + scroll hore). Brand farba klienta (Client červená `#c4161c`) v `--red` premennej.

**Date picker - Looker Studio style.** Jeden pill = popover s dvoma kalendármi (Začiatok/Koniec), preset dropdown, Zrušiť/Použiť (potvrdzujúce tlačidlo, nie auto-apply). Presety: Minulý mesiac, Tento mesiac, Tento rok, Posledných 7/30/90 dní. **Default = TENTO MESIAC DO VČERA**: `DEND` = včera vzhľadom na build (`D.generated - 1`), capnuté na `DMAX` (posledný deň s dátami) - **nikdy neúplný dnešok**. Všetky "to-date" presety končia `DEND`, nie dneškom. JS prepočíta všetky KPI/PPC/PNO/kanály/storná/značky pre ľubovoľný rozsah; YoY = rovnaký rozsah posunutý o rok, MoM = predošlé obdobie (`cmpMode`, `prevRange()`).

**KPI karty.** 6 kariet, **bez emoji**: Obrat bez DPH, Objednávky, Storná, Náklady na PPC, Obrat z PPC kampaní (GA4), PNO (GA4). Prepínač **YoY / MoM** (mení baseline). Pozn.: hlavné "Obrat z PPC" a "PNO" sú z **GA4** (paid kanály = google/cpc + paid social), NIE platform-attributed (to je sekcia "Dva pohľady" nižšie, kde platform-attributed dáva nízke PNO lebo sa prekrýva s organikou/brandom).

**Trend graf - TradingView feel** (najviac iterované):
- **Lineárna os** (nie kategória) s integer indexom (deň/týždeň/mesiac v roku) + `ticks.callback` na label. To umožní plynulý zoom a čistý YoY overlay (oba roky na rovnakom indexe).
- **Čiary** (nie stĺpce): aktuálny rok = plná červená + jemná plocha (`fill rgba(196,22,28,.07)`), minulý rok = sivá prerušovaná (`borderDash:[4,3]`). pointRadius 0, pointHoverRadius 4.
- **AUTO-FIT Y na viditeľný rozsah** (signature TradingView feature): pri pan/zoom X sa Y automaticky prispôsobí dátam v okne (`onPan`/`onZoom` = `autoFitY()` počíta min/max viditeľných bodov, `niceBound()` zaokrúhli na pekné číslo, `chart.update('none')`). Ručné ťahanie po osi = manuál (`yManual=true`), Reset/dvojťuk vráti auto.
- **Granularita Mesačne/Týždenne/Denne v DROPDOWNE** (nie ďalšie taby). Denné dáta sa rátajú v JS z `D.orders` + `D.daily` (netreba meniť pipeline).
- Interakcie: zoom kolieskom (centrovaný na kurzor, `mode:'x'`), pinch na mobile, posun ťahaním, **ťah po hodnotovej osi = mierka výšky**, **dvojťuk = reset**. Zväčšenie = **modal cez celú obrazovku na mobile** (`section.big` 100vw/100vh), spoľahlivý resize po prelayoutovaní (`requestAnimationFrame` + setTimeout 200).
- chartjs-plugin-zoom@2.0.1 + hammerjs (CDN). Hint text **bez inštrukcií** (autor chcel preč zoom/dvojťuk návody) - len `metrika · rok vs rok`.

**Kanály tabuľka.** Source/Medium | Obrat (silný červený bar od začiatku riadku) | Objednávky | Sessions. Z GA4 daily channels. Riadok Spolu. **Na mobile skrátené hlavičky "Obj." / "Sess."** (dual span hfull/hsm) + clip, inak sa prekrývajú v úzkych stĺpcoch.

**Storná tabuľka.** Source/medium z GA4 (transactionId join). **Na mobile: prvých 5 + tlačidlo "Zobraziť všetky storná (N)"** (`.canc-collapsed:not(.canc-open) tr:nth-child(n+6){display:none}`), polia karty **na celú šírku zarovnané vpravo** (`.canc-tbl tbody td{grid-column:1/-1}`).

**Značky a produkty.** Treemap najpredávanejších značiek (ranked tiles). **Top bicykle (značka+model)** = produkty s `bk=1` (heuristika cena/ks ≥ 400 €, dá sa dočistiť cez GMC kategóriu). **Top produkty (BEZ bicyklov)** = `bk=0` - komplementárne k bicyklom, **žiadna duplicita** (predtým oboje ukazovalo to isté lebo bicykle dominujú).

**PPC kampane tab.** Tabuľka Kampaň | Platforma | Stav | Investícia | Kliknutia | CTR | CPC | Obrat | PNO, **date-range aware** (agreguje z dennej histórie). Hore **summary denného budgetu len REÁLNE zobrazovaných kampaní** (aktívne + impresie za 7 dní). **Stĺpce sortovateľné**, riadok Spolu. Dáta sa akumulujú do `data/camp_history.json` (commit-back v CI). **Na mobile kompaktný prehľad** (názov + Investícia + Obrat + PNO) = klik rozbalí plný detail + náhľady. **Náhľady reklám:**
- Meta = klikateľná kreatíva (thumbnail+text) = "Náhľad reklamy na Facebooku" (`preview_shareable_link`). Viď Meta post boosting.
- Google PMAX = **shareable preview link** (červené tlačidlo "Náhľad reklamy v Google Ads", reálny vyrenderovaný náhľad ako Meta) cez `ShareablePreviewService.GenerateShareablePreviews` (`preview_type=UI_PREVIEW`, `asset_group_identifier.asset_group_id`) = `shareable_preview_url`, **14-dňová expirácia, regeneruje sa každým behom** takže nikdy nevyexpiruje. + RSA mockup z textov + obrázkové assety **len z ENABLED asset_group**. (Starý mýtus "Google nemá shareable preview" je NEAKTUÁLNY - má, od Google Ads API v17.1.) Viď PMAX.

---

## 4. Mobile / responsive patterns (gotchas)

- **Graf zoom na mobile:** `touch-action: pan-y` na canvas (plugin si ho stejne prepíše na `none` v aktívnom móde), v `section.big` (fullscreen) `none`. Vertikálny ťah scrolluje stránku, horizontálny pan + pinch idú do grafu.
- **Tabuľky = karty:** skry `thead`, `tr` na `display:grid`, každé `td` má `data-label`, `td::before{content:attr(data-label)}`. Prvý stĺpec = hlavička karty (full width).
- **Collapse pattern:** detail polia skryté cez `:not(.open)`, klik togluje `.open`, indikátor "Detail"/"Zavrieť".
- **Prekrývanie hlavičiek** v úzkych grid stĺpcoch: skrátené labely (dual span) + `overflow:hidden;text-overflow:ellipsis`.
- Hodnoty s medzerou (`€1 788,61`) na mobile `white-space:nowrap`, nech sa nelámu.

---

## 5. Robustnosť a ops gotchas (KRITICKÉ - bez tohto to v cloude padá)

- **GA4 504/503 výpadky** (DeadlineExceeded / Bad Gateway): rozsah 2024-2026 denne je na jeden request pridlhý.
  1. **Chunkovať GA4 query PO ROKOCH** (`ga4_run_chunked`, jeden request na rok) + `timeout=120` + **retry 5x** s backoffom 15/30/45/60/60s.
  2. **GA4 CACHE** (`data/ga4_cache.json`, commit-back v CI): keď GA4 prejde = ulož kanály+txns; keď padne = **použi posledné dobré GA4 + čerstvý zvyšok** (objednávky, PPC náklady) a normálne deployni. Nikdy prázdny report.
  3. **Guard:** ak GA4 padne a niet cache = `exit 3` = build zlyhá = NEdeployuje sa, ostane posledný dobrý deploy.
- **Timing GA4 dát:** GA4 za včerajšok dotečie ~okolo obeda. Preto **cron 2x denne**: ranný ~3:15 (osvieži Shoptet/PPC) + **poobedný ~13:30** (kompletné GA4 kanály). Default rozsah končí včerajškom (DEND) aby ranný neúplný dnešok nevadil.
- **gcloud user token expiruje často** ("Reauthentication failed") - lokálne `gcloud auth login analytics@signity.sk`; v CI **service account** (neexpiruje, OAuth refresh tokeny dlhodobé). (Detail aj v memory `signity_ppc_mcp_gcloud_auth` v projekte.)
- **Cache-control `public, max-age=0, must-revalidate`** hlavičky (vercel.json) - inak mobil drží starú verziu po deploji.
- **Heslo bez prihlasovacieho mena:** Vercel Edge middleware (`deploy-middleware.js`) - vlastný formulár + cookie, beží aj na free pláne. Heslo žije v `PASS` v middleware súbore (NEpíš hodnotu do mozgu).
- **🔴 Claude obmedzenia (DÔLEŽITÉ):** Claude má **deploy dôverných klientskych dát TVRDO ZABLOKOVANÝ** (klasifikované ako data exfiltration, nedá sa prebiť povolením). Deploy s reálnymi dátami spúšťa operátor. ALE **git push + `gh workflow run` Claudovi POVOLENÉ** = preto deploy ide cez **GitHub Actions** (CI robí `vercel deploy`, nie Claude priamo). Claude tiež nesmie vytvárať GCP service accounty / IAM bindings / kľúče - to robí operátor (runbook SETUP-GITHUB.md).

---

## 6. White-label a demo (na ukážku prospektom)

- **build_dashboard.py je parametrizovaný:** `--client "Brand.sk"` + `--assets-dir <dir>`. Placeholdery `__BRAND__` / `__BRANDSHORT__` v `<title>`, PWA mene, logo `alt`. Default zachováva pôvodné správanie.
- **make_demo.py** generuje **vymyslené dáta** (fiktívna značka napr. Veloria.sk, fiktívne brandy/produkty/kampane, sezónnosť + YoY rast, realistické **PNO ~10 %**, kampaňové náklady **konzistentné s KPI**). Demo = bez password gate, hostené ako **samostatný Vercel projekt** (`veloria-demo-site`), verejná URL pre prospekta. Reprodukovateľné: `python make_demo.py && build_dashboard.py --client ... --assets-dir assets-demo`.
- Demo nemá reálne ad previews (fake dáta) - to je feature reálnych dát.

---

## 7. Deploy (Vercel + GitHub Actions)

- Privátny GitHub repo per klient. `.github/workflows/daily.yml`: cron 2x denne, auth cez **GCP service account** (`GCP_SA_KEY` secret, `secretAccessor` na 9 secretoch), build (`run_report.sh`, env `SM_ACCOUNT=""` = aktívny SA, `PYTHON_BIN=python3`), prepare site (index.html + middleware.js + vercel.json + manifest + ikony), `vercel deploy --prod` (secrets `VERCEL_TOKEN/ORG_ID/PROJECT_ID`), commit-back `data/camp_history.json` + `data/ga4_cache.json`.
- **PWA:** manifest.json (`display:standalone`), app ikony (192/512 + apple-touch 180), meta tagy (`apple-mobile-web-app-capable`, theme-color, status-bar-style). Middleware matcher prepúšťa `manifest.json` + `icon-*` bez hesla. iOS cachuje ikonu na ploche = pri zmene zmazať a pridať appku nanovo.
- Setup runbook: `SETUP-GITHUB.md` v repe (bloky A-E: SA, Vercel token, repo, secrets, test run).

---

## 8. Per-klient variácie - čo zmeniť pri novom klientovi

1. **Účty/ID:** GAds customer, Meta act_, GA4 property, Shoptet/WP feed URL = nové secrety v Secret Manageri.
2. **Zdroj objednávok:** Shoptet parser vs WooCommerce REST vs WP/custom = uprav `parse_orders.py` (alebo nový parser, rovnaký výstupný tvar agg.json).
3. **e-com vs leadgen:** 
   - e-com = obrat, objednávky, AOV, ROAS, PNO, značky/produkty, storná.
   - leadgen = **leady, CPL, konverzný pomer, web formuláre** (KPI karty, "kanály"=leady per source/medium, žiadne značky/produkty/storná). Vzor leadgen logiky: Sportwell.
4. **Konverzie:** definuj čo je konverzia (nákup / lead / hovor) v GA4 + Ads/Meta = mení "Obrat z PPC" a PNO/CPL výpočet.
5. **Brand assets:** hero fotka + logo z webu klienta = `assets/`. Brand farba do `--red`.
6. **Platforma webu:** Shoptet (cp1250 feed) / WooCommerce / WP / Magento - každá má iný export, výstupný JSON tvar drž rovnaký.
7. **Bicykle/produkty heuristika:** prahy a kategórie podľa sortimentu klienta (alebo vypni sekciu pri leadgen).

## Súvisí
Reporting · Marketing · GA4 · PMAX · Meta post boosting · Bezpečnosť · Signity (agentúra)
