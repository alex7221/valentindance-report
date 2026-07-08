# Valentindance report — GitHub Actions setup (copy-paste runbook)

Cieľ: report sa raz denne (~4:00) sám vygeneruje v cloude a nasadí na Vercel — bez tvojho Macu.
`gh` aj `vercel` máš prihlásené. Stačí prejsť bloky A–E nižšie (každý je copy-paste).

Prečo to nespúšťa Claude: deploy/publikovanie dôverných dát + tvorba service accountu/credentials
sú tvrdo blokované/zakázané na jeho strane (systémovo, nedá sa prebiť povolením). Preto bloky spúšťaš ty.

---

## A. GCP service account (prístup k secrets, neexpiruje)
Ak by gcloud pýtal login: `gcloud auth login analytics@signity.sk`
```bash
PROJECT=claude-493613; ACC=analytics@signity.sk
SA="report-ci@${PROJECT}.iam.gserviceaccount.com"

gcloud iam service-accounts create report-ci \
  --display-name="Client report CI" --project="$PROJECT" --account="$ACC"

for S in GA4_CLIENT_ID GA4_CLIENT_SECRET GA4_REFRESH_TOKEN \
         ADS_DEVELOPER_TOKEN ADS_CLIENT_ID ADS_CLIENT_SECRET GOOGLE_ADS_REFRESH_TOKEN \
         ADS_LOGIN_CUSTOMER_ID; do
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT" --account="$ACC"
done

gcloud iam service-accounts keys create /tmp/cyklo-ci-key.json \
  --iam-account="$SA" --account="$ACC"
```

## B. Vercel token
Vercel → Account Settings → Tokens → Create Token → skopíruj (budeš ho vkladať v bloku D).

## C. Privátny GitHub repo + push
```bash
cd "."
git init && git add -A && git commit -m "Client report pipeline"
gh repo create valentindance-report --private --source=. --remote=origin --push
```

## D. GitHub secrets (4 ks)
```bash
cd "."
gh secret set GCP_SA_KEY < /tmp/cyklo-ci-key.json
gh secret set VERCEL_TOKEN            # vloží sa interaktívne — prilep token z bloku B
gh secret set VERCEL_ORG_ID --body "team_XXXXXXXX"
gh secret set VERCEL_PROJECT_ID --body "prj_XXXXXXXX"
rm -P /tmp/cyklo-ci-key.json          # zmaž SA kľúč z disku
```

## E. Spusti workflow (test) — potom beží denne sám
```bash
gh workflow run daily.yml
gh run watch        # sleduj priebeh; má skončiť zelene
```
Ak prejde zelene → cron beží denne o ~4:00 (UTC `17 2 * * *`). Hotovo.

---

## Pozn.
- **Heslo na report** (bez mena) je v `deploy-middleware.js` (`PASS`, momentálne `ValentinReport`). Po zmene → `./deploy.sh` alebo push.
- Vercel projekt zatiaľ nie je vytvorený — treba `vercel link`/`vercel project add` pred blokom D (VERCEL_ORG_ID/PROJECT_ID placeholdery nižšie doplň skutočnými).
- Klient nemá Meta ani GMC — žiadny META_ACCESS_TOKEN secret netreba.
- Custom doména: Vercel projekt → Settings → Domains → pridaj napr. `report.valentindance.com` + CNAME v DNS.
- Keď niečo zaškrípe (červený run), pošli mi log z `gh run view` a poradím.
