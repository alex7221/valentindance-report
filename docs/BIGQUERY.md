# BigQuery dátová vrstva (pre škálovanie reportov)

Tento dokument vysvetľuje, ako reporty vedia čítať z **BigQuery** namiesto toho, aby pri
každom builde ťahali dáta priamo z API (Google Ads, Meta, GA4, WooCommerce). Je to voliteľná
nadstavba nad kostrou v tomto repe - default pipeline (priamy API pull) funguje aj bez nej.

> Hotové súbory na zapnutie sú v priečinku **`bigquery/`** (`export_from_bq.py`, `bootstrap.sh`,
> `run_report.sh`, `daily.bq.yml`) — krok-za-krokom návod v `bigquery/README.md`. Tu nižšie je pozadie a architektúra.

## Prečo

Default model: každý build reportu stiahne **celú históriu** (2024-dnes) zo všetkých API,
2× denne. Pri jednom klientovi to ide. Pri portfóliu (~50 klientov) to znamená:

- **Rate limity** - hlavne Meta ads insights agresívne limituje opakované plné pully (vráti 403/500). Keď pull zlyhá, report môže prísť o dáta.
- **Pomalé a krehké buildy** - minúty ťahania pri každom behu.
- **Žiadny spoločný pohľad** na dáta naprieč klientmi.

BigQuery to otáča: dáta sa ťahajú **raz, inkrementálne**, do skladu; reporty z neho len **čítajú**.

## Architektúra

```
INGEST (repo signity-reporting-ingest, GitHub Actions, denne ráno)
  per klient × zdroj: stiahni len posledné ~30 dní z API → zapíš do BQ
     WooCommerce / Google Ads / Meta / GA4
        → BQ dataset <klient>  (projekt claude-493613, lokácia EU)

REPORT (tento repo, per klient)
  export_from_bq.py  →  agg.json + ppc.json   (číta z BQ, žiadne API)
  build_dashboard.py →  HTML  →  Vercel
```

Ingest beží **pred** report cronom, takže BQ má včerajšie dáta skôr, než report build číta.

Sú to **dva repá**:
- **`signity-reporting-ingest`** - plní BQ. Config-driven cez `clients.json` (per klient: dataset, secrety, GA4/Ads/Meta ID, kategórie, kurz...). Jeden ingest pre celé portfólio.
- **report repo klienta** (z tejto kostry) - už neťahá z API, len spustí `export_from_bq.py`, ktorý z BQ zostaví **rovnaký `agg.json`/`ppc.json`**, aký predtým produkovali `parse_orders.py` + `pull_ppc.py`. `build_dashboard.py` sa **nemení**.

## Dátový model

**Dataset per klient** (izolácia dát) - napr. `lebeddie`, `cykloshop`. Tabuľky (DAY-partition podľa `date`, sumy v EUR):

| Tabuľka | Obsah |
|---|---|
| `orders`, `order_lines` | objednávky + položky (e-com) |
| `ga4_channels`, `ga4_txns` | GA4 kanály + transakcie |
| `gads_daily`, `gads_campaigns` | Google Ads náklady/konverzie (denné + kampaňové) |
| `meta_daily`, `meta_campaigns` | Meta spend/konverzie |
| `campaign_meta`, `budget_snapshot`, `creatives_snapshot` | aktuálny stav kampaní, budgety, náhľady |

## Ako ingest funguje (dôležité detaily)

- **Inkrementálne okno:** každý beh ťahá len posledných ~30 dní (kampane ~60), nie celú históriu. Historické dáta sú v BQ zamrznuté z prvotného backfillu a už sa neťahajú.
- **Prečo okno a nie "len nový deň":** nedávne dni sa ešte menia (status objednávky, dotekajúce konverzie, GA4 finalizácia ~48 h). Okno ich drží aktuálne.
- **Idempotentný zápis:** `delete-window + load` - zmaže sa len to okno a nahrá čerstvé. Staršie dni ostávajú → tabuľky rastú dopredu.
- **Resilience (kľúčové):** ingest najprv **stiahne**, a až **pri úspechu** zapíše. Keď zdroj zlyhá (napr. expirovaný Meta token, 403), ten zdroj sa **preskočí** - jeho dáta v BQ **ostanú nedotknuté**, nič sa nezmaže. Ostatné zdroje nabehnú. Ďalší beh (keď token ožije) vynechané dni v rámci okna **sám dorovná**.
- Report build navyše nikdy nenasadí prázdno - číta, čo v BQ je; pre zaseknutý zdroj ukáže posledné dobré hodnoty.

## Koľko to stojí

Pri PPC objemoch **prakticky nič**: dataset je single-digit GB (úložisko vo free tier), batch loady sú zadarmo, queries reportov sa zmestia pod free 1 TB/mesiac. Reálne **~$0/mes**, strop pri zlej hygiene dopytov ~$10/mes. GitHub Actions minúty pre ingest sú vo free tier. Žiadne AI/LLM v behu (čistý Python).

## Ako napojiť klienta na BigQuery

1. **Pridaj klienta do `clients.json`** v `signity-reporting-ingest` (dataset, secrety, ID, kategórie).
2. **Vytvor dataset + tabuľky:** `./schema/bootstrap.sh <dataset>`.
3. **BQ práva pre service account** (robí admin GCP projektu): SA reportu/ingestu potrebuje `roles/bigquery.dataEditor` + `roles/bigquery.jobUser`.
4. **Backfill:** `python3 ingest.py --client <klient> --backfill` (jednorazovo natiahne históriu; pri Mete šetrne kvôli rate limitu).
5. **Prepni report na BQ:** v report repe nahraď v `run_report.sh` kroky `parse_orders.py` + `pull_ppc.py` jedným `export_from_bq.py --dataset <klient>`; z `daily.yml` vyhoď pip inštaláciu API knižníc a commit-back cache (históriu drží BQ).

## Stav

Pilot beží na **Lebeddie** (kompletne v produkcii). Ostatní klienti zatiaľ na default API-pull modeli;
napájajú sa na BQ postupne podľa krokov vyššie.
