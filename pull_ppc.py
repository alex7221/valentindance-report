#!/usr/bin/env python3.11
"""
Valentindance (leadgen, USA) - PPC + GA4 puller (priamo cez API, credentials z GCP Secret Manager).
Denna granularita kvoli date-range pickeru v dashboarde. Nepotrebuje MCP servery.

LEADGEN verzia (nie e-com): ziadny obrat/ROAS/txns. Klient nema CRM/Sheet ani Meta ucet.
"Lead" = 3 GTM click-akcie merane rovnako v GA4 aj Google Ads: Schedule now, Phone, Mail.
  daily:    { "YYYY-MM-DD": {cost_gads, cost_meta, conv_gads, conv_meta} }   # naklad + ad-konverzie (Meta vzdy 0)
  channels: [{d, sm, s, l}]   # per source/medium/den: sessions + leady (GA4 - 3 click eventy spolu)
  + kampane (denne riadky), budgety, RSA previews (na ad-preview sekciu)

Autoritativny pocet leadov je z GA4 (pull_leads.py, rovnake 3 eventy). Tento puller dava
naklad (na CPL) a rozpad leadov per kanal z GA4.

Usage:
  python3.11 pull_ppc.py --range 2025-01 2026-07 --out /tmp/ppc.json
"""
import os, re, sys, json, argparse, subprocess, calendar, datetime as dt
from collections import defaultdict

PROJECT="claude-493613"
# Lokalne: gcloud user ucet. V CI (GitHub Actions): SM_ACCOUNT="" -> aktivny service account.
ACCOUNT=os.environ.get("SM_ACCOUNT","analytics@signity.sk")
GA4_PROPERTY="539266001"; GADS_CUSTOMER="6702239544"
LEAD_EVENTS=["click_schedule_now","click_phone","click_mail"]   # GA4 eventName (= Google Ads GTM konverzne akcie nizsie)
ADS_LEAD_ACTIONS={"GTM | Click Schedule now","GTM | Click phone","GTM | Click mail"}

_cache={}
def sm(secret):
    if secret in _cache: return _cache[secret]
    cmd=["gcloud","secrets","versions","access","latest","--secret",secret,"--project",PROJECT]
    if ACCOUNT: cmd+=["--account",ACCOUNT]
    v=subprocess.run(cmd,capture_output=True,text=True)
    if v.returncode!=0: raise RuntimeError(f"SM {secret}: {v.stderr[:160]}")
    _cache[secret]=v.stdout.strip(); return _cache[secret]

def gads_mcc():
    return re.sub(r"\D","",sm("ADS_LOGIN_CUSTOMER_ID"))

def mbounds(m):
    y,mo=int(m[:4]),int(m[5:7]); return f"{m}-01", f"{m}-{calendar.monthrange(y,mo)[1]:02d}"

# ---------- GA4 ----------
def ga4_client():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    creds=Credentials(token=None, refresh_token=sm("GA4_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token", client_id=sm("GA4_CLIENT_ID"),
        client_secret=sm("GA4_CLIENT_SECRET"), scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    creds.refresh(Request()); return BetaAnalyticsDataClient(credentials=creds)

import time as _time
def ga4_run_chunked(client, build_req, start, end, timeout=120, retries=5):
    """GA4 RunReport rozdeleny po kalendarnych rokoch - dlhy rozsah inak pada na 504.
    build_req(cs,ce)->RunReportRequest. Retry s backoffom (15/30/45/60/60s)."""
    sy, ey = int(start[:4]), int(end[:4])
    for yr in range(sy, ey+1):
        cs = start if yr == sy else f"{yr}-01-01"
        ce = end   if yr == ey else f"{yr}-12-31"
        if cs > ce: continue
        req = build_req(cs, ce); last = None
        for attempt in range(retries+1):
            try:
                r = client.run_report(req, timeout=timeout)
                for row in r.rows: yield row
                last = None; break
            except Exception as e:
                last = e
                if attempt < retries:
                    _time.sleep(min(60, 15*(attempt+1)))
        if last is not None:
            raise last

def ga4_channels_daily(client,start,end):
    """[{d,sm,s,l}] - denne sessions + leady (3 click eventy) per source/medium.
    Dva reporty (sessions / leady) zmergovane podla (den, source/medium)."""
    from google.analytics.data_v1beta.types import (RunReportRequest,DateRange,Dimension,Metric,
        FilterExpression,Filter)
    # 1) sessions per den+source/medium
    b_sess=lambda cs,ce: RunReportRequest(property=f"properties/{GA4_PROPERTY}",
        dimensions=[Dimension(name="date"),Dimension(name="sessionSourceMedium")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=cs,end_date=ce)],limit=300000)
    # 2) lead-click count per den+source/medium (filter eventName in LEAD_EVENTS)
    lead_filter=FilterExpression(filter=Filter(field_name="eventName",
        in_list_filter=Filter.InListFilter(values=LEAD_EVENTS)))
    b_lead=lambda cs,ce: RunReportRequest(property=f"properties/{GA4_PROPERTY}",
        dimensions=[Dimension(name="date"),Dimension(name="sessionSourceMedium")],
        metrics=[Metric(name="eventCount")], dimension_filter=lead_filter,
        date_ranges=[DateRange(start_date=cs,end_date=ce)],limit=300000)
    agg=defaultdict(lambda:{"s":0,"l":0})
    for row in ga4_run_chunked(client,b_sess,start,end):
        ymd=row.dimension_values[0].value
        key=(f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}",row.dimension_values[1].value)
        agg[key]["s"]+=int(float(row.metric_values[0].value or 0))
    for row in ga4_run_chunked(client,b_lead,start,end):
        ymd=row.dimension_values[0].value
        key=(f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}",row.dimension_values[1].value)
        agg[key]["l"]+=int(float(row.metric_values[0].value or 0))
    out=[]
    for (d,sm_),v in agg.items():
        if v["s"]==0 and v["l"]==0: continue
        out.append({"d":d,"sm":sm_,"s":v["s"],"l":v["l"]})
    return out

def ga4_event_daily(client,start,end,event):
    """{d:count} - denny pocet danej GA4 udalosti (filter na eventName)."""
    from google.analytics.data_v1beta.types import (RunReportRequest,DateRange,Dimension,Metric,
        FilterExpression,Filter)
    flt=FilterExpression(filter=Filter(field_name="eventName",
        string_filter=Filter.StringFilter(value=event)))
    b=lambda cs,ce: RunReportRequest(property=f"properties/{GA4_PROPERTY}",
        dimensions=[Dimension(name="date")],metrics=[Metric(name="eventCount")],
        dimension_filter=flt,date_ranges=[DateRange(start_date=cs,end_date=ce)],limit=300000)
    out={}
    for row in ga4_run_chunked(client,b,start,end):
        ymd=row.dimension_values[0].value
        out[f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"]=int(float(row.metric_values[0].value or 0))
    return out

# ---------- Google Ads ----------
def gads_daily(start,end):
    os.environ["GOOGLE_ADS_USE_PROTO_PLUS"]="True"
    from google.ads.googleads.client import GoogleAdsClient
    cfg={"developer_token":sm("ADS_DEVELOPER_TOKEN"),"client_id":sm("ADS_CLIENT_ID"),
         "client_secret":sm("ADS_CLIENT_SECRET"),"refresh_token":sm("GOOGLE_ADS_REFRESH_TOKEN"),
         "login_customer_id":gads_mcc(),"use_proto_plus":True}
    svc=GoogleAdsClient.load_from_dict(cfg).get_service("GoogleAdsService")
    q=(f"SELECT metrics.cost_micros, metrics.conversions, segments.date "
       f"FROM customer WHERE segments.date BETWEEN '{start}' AND '{end}'")
    by=defaultdict(lambda:{"cost":0.0,"conv":0.0})
    for batch in svc.search_stream(customer_id=GADS_CUSTOMER,query=q):
        for row in batch.results:
            day=str(row.segments.date)
            by[day]["cost"]+=row.metrics.cost_micros/1_000_000
            by[day]["conv"]+=row.metrics.conversions
    return {d:{"cost":round(v["cost"],2),"conv":round(v["conv"],1)} for d,v in by.items()}

def _gads_client():
    os.environ["GOOGLE_ADS_USE_PROTO_PLUS"]="True"
    from google.ads.googleads.client import GoogleAdsClient
    cfg={"developer_token":sm("ADS_DEVELOPER_TOKEN"),"client_id":sm("ADS_CLIENT_ID"),
         "client_secret":sm("ADS_CLIENT_SECRET"),"refresh_token":sm("GOOGLE_ADS_REFRESH_TOKEN"),
         "login_customer_id":gads_mcc(),"use_proto_plus":True}
    return GoogleAdsClient.load_from_dict(cfg)
def _gads_svc():
    return _gads_client().get_service("GoogleAdsService")

# ---------- Campaigns (Google Ads) ----------
def gads_campaigns_daily(start,end):
    svc=_gads_svc()
    q=(f"SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, segments.date,"
       f" metrics.cost_micros, metrics.clicks, metrics.impressions"
       f" FROM campaign WHERE segments.date BETWEEN '{start}' AND '{end}' AND metrics.impressions > 0")
    camps={}; rows=[]
    for batch in svc.search_stream(customer_id=GADS_CUSTOMER,query=q):
        for r in batch.results:
            cid="g"+str(r.campaign.id); m=r.metrics
            camps[cid]={"name":r.campaign.name,"status":r.campaign.status.name,
                "plat":"Google Ads","type":r.campaign.advertising_channel_type.name}
            rows.append({"cid":cid,"d":str(r.segments.date),"co":round(m.cost_micros/1e6,2),
                "cl":int(m.clicks),"im":int(m.impressions),"cv":0.0})
    # cv = LEN 3 lead-akcie (Schedule now / Phone / Mail), nie vsetky konverzie spolu
    qw=(f"SELECT campaign.id, segments.date, segments.conversion_action_name, metrics.conversions"
        f" FROM campaign WHERE segments.date BETWEEN '{start}' AND '{end}' AND metrics.conversions > 0")
    wf={}
    for batch in svc.search_stream(customer_id=GADS_CUSTOMER,query=qw):
        for r in batch.results:
            if r.segments.conversion_action_name not in ADS_LEAD_ACTIONS: continue
            key=("g"+str(r.campaign.id),str(r.segments.date))
            wf[key]=wf.get(key,0.0)+r.metrics.conversions
    for row in rows:
        row["cv"]=round(wf.get((row["cid"],row["d"]),0.0),1)
    return camps,rows

def gads_budgets():
    svc=_gads_svc()
    q=("SELECT campaign.id, campaign_budget.amount_micros"
       " FROM campaign WHERE campaign.status='ENABLED'")
    by={}
    for batch in svc.search_stream(customer_id=GADS_CUSTOMER,query=q):
        for r in batch.results:
            by["g"+str(r.campaign.id)]=round(r.campaign_budget.amount_micros/1e6,2)
    return by

def gads_rsa(start,end):
    svc=_gads_svc()
    q=("SELECT campaign.id, ad_group_ad.ad.responsive_search_ad.headlines,"
       " ad_group_ad.ad.responsive_search_ad.descriptions, ad_group_ad.ad.final_urls"
       " FROM ad_group_ad WHERE campaign.status='ENABLED' AND ad_group_ad.status='ENABLED'"
       " AND ad_group_ad.ad.type='RESPONSIVE_SEARCH_AD'")
    by={}
    for batch in svc.search_stream(customer_id=GADS_CUSTOMER,query=q):
        for r in batch.results:
            cid="g"+str(r.campaign.id)
            rsa=r.ad_group_ad.ad.responsive_search_ad
            heads=[a.text for a in rsa.headlines][:6]; descs=[a.text for a in rsa.descriptions][:3]
            url=list(r.ad_group_ad.ad.final_urls)[:1]
            by.setdefault(cid,[]).append({"heads":heads,"descs":descs,"url":url[0] if url else ""})
    return {cid:v[:3] for cid,v in by.items()}

def safe(fn,label):
    try: return fn()
    except Exception as e:
        print(f"  [WARN] {label}: {type(e).__name__}: {str(e)[:180]}",file=sys.stderr); return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--range",nargs=2,metavar=("START","END"),required=True)
    ap.add_argument("--out",default="/tmp/ppc.json")
    a=ap.parse_args()
    s,_=mbounds(a.range[0]); _,e=mbounds(a.range[1])
    today=dt.date.today().isoformat(); e_ga=min(e,today)
    print(f"Range {s}..{e}; GA4 end capped {e_ga}")

    print("GA4 ..."); cl=safe(ga4_client,"ga4_client")
    chan=safe(lambda:ga4_channels_daily(cl,s,e_ga),"ga4_channels_daily") if cl else None
    # GA4 cache (data/ga4_cache.json, commit-back v CI): GA4 prejde -> uloz; padne -> pouzi posledne dobre.
    cache_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","ga4_cache.json")
    if chan is not None:
        try:
            os.makedirs(os.path.dirname(cache_path),exist_ok=True)
            json.dump({"asof":today,"channels":chan},open(cache_path,"w",encoding="utf-8"),
                      ensure_ascii=False,separators=(",",":"))
            print(f"  GA4 cache aktualizovana ({len(chan)} channel rows, asof {today})")
        except Exception as ex:
            print(f"  [WARN] GA4 cache save zlyhal: {ex}",file=sys.stderr)
    else:
        if os.path.exists(cache_path):
            try:
                c=json.load(open(cache_path,encoding="utf-8"))
                chan=c.get("channels",[])
                print(f"  [WARN] GA4 nedostupne - pouzivam cache (asof {c.get('asof')}, {len(chan)} rows).",file=sys.stderr)
            except Exception as ex:
                print(f"[FATAL] GA4 padlo a cache sa neda nacitat ({ex}).",file=sys.stderr); sys.exit(3)
        else:
            print("[FATAL] GA4 padlo a niet cache (prvy beh?).",file=sys.stderr); sys.exit(3)

    print("Google Ads ..."); gd=safe(lambda:gads_daily(s,e),"gads") or {}

    # --- Campaigns: denny pull za ~5 mes., merge do perzistentneho storu ---
    cend=min(e,today)
    cs=(dt.date.fromisoformat(cend)-dt.timedelta(days=60)).isoformat()
    print(f"Campaigns Google Ads ({cs}..{cend}) ..."); gc=safe(lambda:gads_campaigns_daily(cs,cend),"gads_campaigns") or ({},[])
    new_camps=gc[0]; new_rows=gc[1]

    store_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","camp_history.json")
    os.makedirs(os.path.dirname(store_path),exist_ok=True)
    store={"daily":[],"campaigns":{}}
    if os.path.exists(store_path):
        try: store=json.load(open(store_path,encoding="utf-8"))
        except Exception: pass
    store["daily"]=[r for r in store.get("daily",[]) if r["d"]<cs]+new_rows
    store["campaigns"].update(new_camps); store["updated"]=today
    json.dump(store,open(store_path,"w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))

    camps=store["campaigns"]; camp_daily=store["daily"]
    dts=[r["d"] for r in camp_daily]
    camp_window={"start":min(dts),"end":max(dts)} if dts else {"start":cs,"end":cend}
    active=[c for c,v in camps.items() if v["status"] in ("ENABLED","ACTIVE")]
    print(f"  campaigns: {len(camps)} (active {len(active)}) | history rows {len(camp_daily)}")

    print("Budgets ..."); gbud=safe(gads_budgets,"gads_budgets") or {}
    rstart=(dt.date.fromisoformat(cend)-dt.timedelta(days=6)).isoformat()
    imp7={}
    for r in new_rows:
        if r["d"]>=rstart: imp7[r["cid"]]=imp7.get(r["cid"],0)+r["im"]
    served={c for c,v in imp7.items() if v>0}
    gbud={c:v for c,v in gbud.items() if c in served}
    budget_total={"gads":round(sum(gbud.values()),2),"meta":0.0,
                  "total":round(sum(gbud.values()),2),"count":len(gbud)}
    print(f"  budget z {len(gbud)} realne zobrazovanych kampani")

    print("Creatives ..."); rsa=safe(lambda:gads_rsa(cs,cend),"gads_rsa") or {}

    days=sorted(set(gd))
    daily={}
    for d in days:
        g=gd.get(d)
        daily[d]={"cost_gads":g["cost"] if g else 0.0,"conv_gads":g["conv"] if g else 0.0,
                  "cost_meta":0.0,"conv_meta":0.0}
    out={"daily":daily,"channels":chan or [],
         "campaigns":camps,"camp_daily":camp_daily,"camp_window":camp_window,
         "budgets":budget_total,"rsa":rsa,"gimgs":{},"gprev":{},"creatives":{}}
    json.dump(out,open(a.out,"w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))
    tc=sum(v["cost_gads"] for v in daily.values())
    print(f"Days with PPC: {len(daily)} | total cost ${tc:,.0f} | channel rows: {len(out['channels'])}")
    print(f"Campaigns: {len(camps)} | daily {len(camp_daily)} | budget/den ${budget_total['total']} | rsa {len(rsa)}")
    print("Wrote",a.out)

if __name__=="__main__":
    main()
