# Valentindance dashboard report - kontext pre Claude Code

Leadgen klient (tanečné štúdio, USA). Nemá CRM/Google Sheet, nemá Meta, nemá GMC.
"Lead" = 3 GTM click-akcie merané rovnako v GA4 aj Google Ads: Schedule now, Phone, Mail.
Mena: USD ($), nie EUR - účet Google Ads 670-223-9544 beží v USD.

## Účty
- Google Ads: 670-223-9544 (6702239544 bez pomlčiek v skriptoch)
- GA4 Property: 539266001
- GMC / Meta: nemá

## Pravidlá
- Credentials VŽDY do Google Secret Manager, nikdy plaintext na disk, nikdy do chatu, nikdy do repa.
- Reálne klientske dáta (`data/*.json`, PII CSV, reálne IDs/heslá) NIKDY necommituj. `.gitignore` to chráni.
- Heslo v `deploy-middleware.js` (momentálne `ValentinReport`) - zmena len na priame želanie.
- Pri editácii inline JS v `build_dashboard.py`: backtick (nie apostrof) na template literály, over `node --check`.
- Štýl: bez emoji, šípok, dlhých pomlčiek, kučeravých úvodzoviek. Vecne.

## Pipeline
`run_report.sh` = pull_leads.py (GA4 - 3 click eventy, žiadny Sheet) + pull_ppc.py (GA4/Ads, bez Meta)
+ build_dashboard.py (HTML, upravená leadgen šablóna bez webform funnelu a kategórií zo Sheetu).
Deploy = GitHub Actions CI (`SETUP-GITHUB.md`, ešte nespustené - treba GCP service account + Vercel projekt).
Lokálny náhľad: `python3 -m http.server 8765` a otvor `report.html`.
