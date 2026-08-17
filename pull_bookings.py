#!/usr/bin/env python3.11
"""
Valentindance - Square Bookings puller.
Taha skutocne rezervacie zo Square Appointments (nie len GA4/Ads kliky ako pull_leads.py),
aby report vedel ukazat realny lead -> booking rate.

Square List Bookings API filtruje len podla start_at (termin rezervacie), nie created_at,
a max. rozsah jedneho volania su 31 dni - preto sa taha po 31-dnovych oknach od START po
dnesok + buffer (zachytit aj uz zarezervovane buduce terminy). Agregacia v tomto vystupe je
podla created_at (kedy bola rezervacia spravena), aby sedela s mesacnym clenenim leadov/PPC.

OAuth token je v data/square_tokens.json (vid square_oauth_exchange.sh). Pri expiracii
(alebo tesne pred nou) sa automaticky obnovi cez refresh_token - klientka uz nemusi znova
nic klikat, potrebuje sa len SQUARE_CLIENT_SECRET v .env.

Cache (data/bookings_cache.json): rovnaky princip ako leads_cache.json - API prejde -> uloz;
API padne -> pouzi posledne dobre; bez cache pri prvom zlyhani exit(3), nech sa nedeployuje
prazdny report.

Usage:
  python3.11 pull_bookings.py --out /tmp/bookings.json
"""
import os, sys, json, argparse, datetime as dt, subprocess
from collections import OrderedDict, defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS_PATH = os.path.join(HERE, "data", "square_tokens.json")
ENV_PATH = os.path.join(HERE, ".env")
TOKEN_URL = "https://connect.squareup.com/oauth2/token"
BOOKINGS_URL = "https://connect.squareup.com/v2/bookings"
APP_ID = "sq0idp-ZMgxj6tD5CW0iMEvVkr7hg"
SQUARE_VERSION = "2024-08-21"
START = "2025-01-01"
FUTURE_BUFFER_DAYS = 90


def read_client_secret():
    if not os.path.exists(ENV_PATH):
        return None
    for line in open(ENV_PATH, encoding="utf-8"):
        if line.startswith("SQUARE_CLIENT_SECRET="):
            return line.strip().split("=", 1)[1]
    return None


def curl_json(url, headers, method="GET", data=None):
    cmd = ["curl", "-s", "-X", method, url]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def refresh_access_token(tokens):
    secret = read_client_secret()
    if not secret:
        raise RuntimeError("SQUARE_CLIENT_SECRET chyba v .env - neviem obnovit token.")
    resp = curl_json(TOKEN_URL, {"Square-Version": SQUARE_VERSION}, "POST", {
        "client_id": APP_ID, "client_secret": secret,
        "refresh_token": tokens["refresh_token"], "grant_type": "refresh_token",
    })
    if "access_token" not in resp:
        raise RuntimeError(f"Square token refresh zlyhal: {resp}")
    json.dump(resp, open(TOKENS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return resp


def load_tokens():
    tokens = json.load(open(TOKENS_PATH, encoding="utf-8"))
    expires = dt.datetime.fromisoformat(tokens["expires_at"].replace("Z", "+00:00"))
    if expires - dt.datetime.now(dt.timezone.utc) < dt.timedelta(days=2):
        tokens = refresh_access_token(tokens)
    return tokens


def list_bookings_window(token, start_min, start_max):
    bookings = []
    cursor = None
    while True:
        url = f"{BOOKINGS_URL}?limit=200&start_at_min={start_min}&start_at_max={start_max}"
        if cursor:
            url += f"&cursor={cursor}"
        resp = curl_json(url, {"Authorization": f"Bearer {token}", "Square-Version": SQUARE_VERSION})
        if resp.get("errors"):
            raise RuntimeError(f"Square bookings error: {resp['errors']}")
        bookings.extend(resp.get("bookings", []))
        cursor = resp.get("cursor")
        if not cursor:
            break
    return bookings


def pull_all_bookings(token, start_date, end_date):
    """31-dnove okna od start_date po end_date (vratane), dedup podla id."""
    seen = {}
    cur = start_date
    while cur <= end_date:
        win_end = min(cur + dt.timedelta(days=30), end_date)
        smin = cur.strftime("%Y-%m-%dT00:00:00Z")
        smax = (win_end + dt.timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        for b in list_bookings_window(token, smin, smax):
            seen[b["id"]] = b
        cur = win_end + dt.timedelta(days=1)
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/bookings.json")
    args = ap.parse_args()

    today = dt.date.today()
    cache_path = os.path.join(HERE, "data", "bookings_cache.json")

    try:
        tokens = load_tokens()
        start_date = dt.date.fromisoformat(START)
        end_date = today + dt.timedelta(days=FUTURE_BUFFER_DAYS)
        bookings = pull_all_bookings(tokens["access_token"], start_date, end_date)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        json.dump({"asof": today.isoformat(), "bookings": bookings},
                   open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"  Square bookings cache aktualizovana (asof {today}, {len(bookings)} rezervacii)")
    except Exception as ex:
        if os.path.exists(cache_path):
            try:
                c = json.load(open(cache_path, encoding="utf-8"))
                bookings = c.get("bookings", [])
                print(f"  [WARN] Square nedostupny ({type(ex).__name__}: {ex}) - pouzivam cache "
                      f"(asof {c.get('asof')}).", file=sys.stderr)
            except Exception as ex2:
                print(f"[FATAL] Square padol a cache sa neda nacitat ({ex2}).", file=sys.stderr); sys.exit(3)
        else:
            print(f"[FATAL] Square padol ({ex}) a niet cache (prvy beh?).", file=sys.stderr); sys.exit(3)

    by_month = defaultdict(lambda: defaultdict(int))
    for b in bookings:
        month = b["created_at"][:7]
        by_month[month][b["status"]] += 1
    monthly = OrderedDict()
    for mk in sorted(by_month):
        statuses = dict(by_month[mk])
        monthly[mk] = {"total": sum(statuses.values()), "statuses": statuses}

    result = {
        "generated": today.isoformat(),
        "monthly": monthly,
        "bookings": [{"id": b["id"], "status": b["status"], "created_at": b["created_at"],
                      "start_at": b["start_at"]} for b in bookings],
    }
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    cnt = Counter(b["status"] for b in bookings)
    print(f"Months {len(monthly)} | bookings {len(bookings)} | statuses {dict(cnt)}")


if __name__ == "__main__":
    main()
