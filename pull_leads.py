#!/usr/bin/env python3.11
"""
Valentindance - GA4-driven lead puller (bez Google Sheet / CRM).
Klient nema CRM ani samostatny web formular - "lead" = GTM click-akcia (Schedule now /
Phone / Mail), merana rovnako v GA4 (eventName) aj v Google Ads (konverzna akcia).

Tento skript cita GA4 denne pocty tychto 3 eventov a rozbali ich na jednotlive "lead"
zaznamy (rovnaky tvar agg.json ako povodny sheet-based parser), aby build_dashboard.py
fungoval bez zmien v Python vrstve. Ziadne credentials na disk - vsetko cez
Secret Manager (reuse pull_ppc.ga4_client/ga4_event_daily).

GA4 cache (data/leads_cache.json, commit-back v CI, rovnaky princip ako ga4_cache.json
pre kanaly): GA4 prejde -> uloz; GA4 padne (napr. prechodne PERMISSION_DENIED) -> pouzi
posledne dobre. Bez cache pri prvom zlyhani exit(3), nech sa nedeployuje prazdny report.

Usage:
  python3.11 pull_leads.py --out /tmp/agg.json
"""
import os, sys, json, argparse, datetime as dt
from collections import OrderedDict, defaultdict, Counter
import pull_ppc as P

EVENTS = OrderedDict([
    ("click_schedule_now", "SCHEDULE"),
    ("click_phone", "PHONE"),
    ("click_mail", "MAIL"),
])
CATS = list(EVENTS.values())
START = "2025-01-01"

def pull_events_daily(end):
    """{event: {date: count}} - cerstvy pull vsetkych 3 eventov z GA4. Vyhodi vynimku pri zlyhani."""
    client = P.ga4_client()
    return {event: P.ga4_event_daily(client, START, end, event) for event in EVENTS}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/agg.json")
    args = ap.parse_args()

    today = dt.date.today().isoformat()
    end = today
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "leads_cache.json")

    try:
        events_daily = pull_events_daily(end)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        json.dump({"asof": today, "events": events_daily}, open(cache_path, "w", encoding="utf-8"),
                   ensure_ascii=False, separators=(",", ":"))
        print(f"  GA4 leads cache aktualizovana (asof {today})")
    except Exception as ex:
        if os.path.exists(cache_path):
            try:
                c = json.load(open(cache_path, encoding="utf-8"))
                events_daily = c.get("events", {})
                print(f"  [WARN] GA4 nedostupne ({type(ex).__name__}) - pouzivam cache "
                      f"(asof {c.get('asof')}).", file=sys.stderr)
            except Exception as ex2:
                print(f"[FATAL] GA4 padlo a cache sa neda nacitat ({ex2}).", file=sys.stderr); sys.exit(3)
        else:
            print(f"[FATAL] GA4 padlo ({ex}) a niet cache (prvy beh?).", file=sys.stderr); sys.exit(3)

    leads = []
    for event, cat in EVENTS.items():
        for d, n in events_daily.get(event, {}).items():
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
        "client": "Valentin Dance", "type": "leadgen", "generated": today,
        "categories": CATS, "list_since": START[:7],
        "date_min": dmin, "date_max": dmax,
        "monthly": monthly, "leads": leads,
    }
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    cnt = Counter(l["cat"] for l in leads)
    print(f"Months {len(monthly)} | leads {len(leads)} | range {dmin}..{dmax}")
    print("po kategorii:", dict(cnt))

if __name__ == "__main__":
    main()
