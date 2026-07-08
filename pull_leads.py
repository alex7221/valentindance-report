#!/usr/bin/env python3.11
"""
Valentindance - GA4-driven lead puller (bez Google Sheet / CRM).
Klient nema CRM ani samostatny web formular - "lead" = GTM click-akcia (Schedule now /
Phone / Mail), merana rovnako v GA4 (eventName) aj v Google Ads (konverzna akcia).

Tento skript cita GA4 denne pocty tychto 3 eventov a rozbali ich na jednotlive "lead"
zaznamy (rovnaky tvar agg.json ako povodny sheet-based parser), aby build_dashboard.py
fungoval bez zmien v Python vrstve. Ziadne credentials na disk - vsetko cez
Secret Manager (reuse pull_ppc.ga4_client/ga4_event_daily).

Usage:
  python3.11 pull_leads.py --out /tmp/agg.json
"""
import argparse, datetime as dt
from collections import OrderedDict, defaultdict
import pull_ppc as P

EVENTS = OrderedDict([
    ("click_schedule_now", "SCHEDULE"),
    ("click_phone", "PHONE"),
    ("click_mail", "MAIL"),
])
CATS = list(EVENTS.values())
START = "2025-01-01"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/agg.json")
    args = ap.parse_args()

    end = dt.date.today().isoformat()
    client = P.ga4_client()

    leads = []
    for event, cat in EVENTS.items():
        daily = P.ga4_event_daily(client, START, end, event)
        for d, n in daily.items():
            for _ in range(n):
                leads.append({"d": d, "cat": cat, "wf": 1})
    leads.sort(key=lambda x: x["d"])

    by_month = defaultdict(lambda: defaultdict(int))
    for l in leads:
        by_month[l["d"][:7]][l["cat"]] += 1
    monthly = OrderedDict()
    for mk in sorted(by_month):
        cats = {c: by_month[mk].get(c, 0) for c in CATS}
        total = sum(cats.values())
        monthly[mk] = {"leads": total, "webform": total, "cats": cats}

    keys = list(monthly.keys())
    dmin = leads[0]["d"] if leads else (keys[0] + "-01" if keys else START)
    dmax = leads[-1]["d"] if leads else (keys[-1] + "-28" if keys else end)
    result = {
        "client": "Valentin Dance", "type": "leadgen", "generated": dt.date.today().isoformat(),
        "categories": CATS, "list_since": START[:7],
        "date_min": dmin, "date_max": dmax,
        "monthly": monthly, "leads": leads,
    }
    import json
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    from collections import Counter
    cnt = Counter(l["cat"] for l in leads)
    print(f"Months {len(monthly)} | leads {len(leads)} | range {dmin}..{dmax}")
    print("po kategorii:", dict(cnt))

if __name__ == "__main__":
    main()
