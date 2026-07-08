#!/usr/bin/env python3.11
"""
Valentindance (leadgen, USA) - generator interaktivneho HTML dashboardu s DATE-RANGE pickerom.
Embedne per-lead/denne data; JS prepocita cisla pre lubovolny rozsah od-do.
Hlavne KPI: leady spolu (Schedule now + Phone + Mail klik). PPC: naklad + CPA.
Trend graf = tento rok vs minuly rok (mesacne/tyzdenne/denne).

Usage:
  python3.11 build_dashboard.py --agg data/agg.json --ppc /tmp/ppc.json --out report.html
"""
import json, argparse, datetime as dt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--agg",required=True)
    ap.add_argument("--ppc",default=None)
    ap.add_argument("--out",required=True)
    ap.add_argument("--client",default="Your Brand")
    ap.add_argument("--assets-dir",default=None)
    a=ap.parse_args()
    agg=json.load(open(a.agg,encoding="utf-8"))
    ppc=json.load(open(a.ppc,encoding="utf-8")) if a.ppc else {"daily":{},"channels":[]}
    import os
    here=os.path.dirname(os.path.abspath(__file__))
    adir=a.assets_dir or os.path.join(here,"assets")
    def asset(name):
        p=os.path.join(adir,name)
        return open(p,encoding="utf-8").read().strip() if os.path.exists(p) else ""
    DATA={
        "client":a.client,"generated":dt.date.today().isoformat(),
        "date_min":agg["date_min"],"date_max":agg["date_max"],"list_since":agg["list_since"],
        "leads":agg["leads"],"monthly":agg["monthly"],"categories":agg["categories"],
        "daily":ppc.get("daily",{}),"chan":ppc.get("channels",[]),
        "formstart":ppc.get("form_start",{}),"formview":ppc.get("form_view",{}),
        "campaigns":ppc.get("campaigns",{}),"camp_daily":ppc.get("camp_daily",[]),
        "camp_window":ppc.get("camp_window",{}),"budgets":ppc.get("budgets",{}),
        "rsa":ppc.get("rsa",{}),"gimgs":ppc.get("gimgs",{}),"gprev":ppc.get("gprev",{}),"creatives":ppc.get("creatives",{}),
        "searchTerms":ppc.get("search_terms",[]),"searchTermsWindow":ppc.get("search_terms_window",{}),
        "logo":asset("logo.b64"),"hero":asset("hero.b64"),
    }
    html=TEMPLATE.replace("/*__DATA__*/",json.dumps(DATA,ensure_ascii=False,separators=(",",":")))
    html=html.replace("__BRAND__",a.client).replace("__BRANDSHORT__",a.client.split(".")[0])
    open(a.out,"w",encoding="utf-8").write(html)
    print("Wrote",a.out,"| leads",len(agg["leads"]),"| months",len(agg["monthly"]),
          "| ppc days",len(DATA["daily"]),"chan",len(DATA["chan"]),"| HTML",len(html)//1024,"KB")

TEMPLATE=r"""<!DOCTYPE html>
<html lang="sk"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__BRAND__ — výkonnostný report</title>
<meta name="theme-color" content="#00bed4">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="__BRANDSHORT__">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<style>
  :root{--red:#f72d7f;--red-d:#c91a63;--ink:#0a0c0e;--ink2:#3a4046;--mut:#7b848c;
    --line:#e7eaed;--bg:#f4f6f8;--card:#fff;--good:#0e8a3e;--bad:#c4161c;--soft:#fce6f0;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.45;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1180px;margin:0 auto;padding:24px 22px 80px}
  .hero{position:sticky;top:0;z-index:100;width:100%;background:#0a0c0e center 38%/cover no-repeat;
    border-bottom:3px solid var(--red);box-shadow:0 6px 22px rgba(10,12,14,.18)}
  .hero::before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,12,14,.86),rgba(10,12,14,.45) 55%,rgba(10,12,14,.28));pointer-events:none}
  .hero-inner{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:calc(13px + env(safe-area-inset-top,0px)) 22px 13px;
    display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap}
  .brand{display:flex;align-items:center;gap:13px}
  .logo-chip{background:#fff;border-radius:11px;padding:9px 14px;box-shadow:0 5px 16px rgba(0,0,0,.3);display:inline-flex}
  .logo-img{height:34px;display:block}
  .hero .pmeta{color:#e2e6e9;text-shadow:0 1px 3px rgba(0,0,0,.65)}
  .ctrl{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
  .pmeta{color:var(--mut);font-size:11.5px}
  .dr{position:relative}
  .dr-trigger{display:inline-flex;align-items:center;gap:9px;border:1.5px solid var(--line);background:#fff;
    border-radius:10px;padding:9px 13px;font-size:14px;font-weight:700;color:var(--ink);cursor:pointer;
    font-family:inherit;min-width:250px;justify-content:space-between}
  .dr-trigger:hover{border-color:var(--red)}
  .dr-trigger>span{flex:1;text-align:left}
  .dr-pop{position:absolute;right:0;top:calc(100% + 8px);z-index:50;background:#fff;border:1px solid var(--line);
    border-radius:14px;box-shadow:0 18px 50px rgba(10,12,14,.18);padding:14px;width:560px}
  .dr-pop[hidden]{display:none}
  .dr-head{display:flex;justify-content:flex-end;margin-bottom:8px}
  .dr-preset{font-size:13px;font-weight:700;border:1.5px solid var(--line);border-radius:9px;padding:7px 28px 7px 11px;background:#fff;cursor:pointer;font-family:inherit;color:var(--ink);
    -webkit-appearance:none;appearance:none;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237b848c' stroke-width='3'><path d='M6 9l6 6 6-6'/></svg>");
    background-repeat:no-repeat;background-position:right 9px center}
  .dr-body{display:flex;gap:18px}
  .dr-cal{flex:1}
  .dr-cap{font-size:12.5px;font-weight:800;text-align:center;color:var(--ink2);margin-bottom:8px}
  .dr-nav{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
  .dr-nav span{font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.4px}
  .dr-nav button{border:0;background:transparent;font-size:17px;line-height:1;color:var(--ink2);cursor:pointer;padding:3px 9px;border-radius:7px}
  .dr-nav button:hover{background:#f0f2f4;color:var(--red)}
  .dr-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
  .dr-wd{font-size:10.5px;font-weight:700;color:var(--mut);text-align:center;padding:4px 0}
  .dr-d{font-size:12.5px;text-align:center;padding:7px 0;border-radius:8px;cursor:pointer;font-weight:600;color:var(--ink);user-select:none}
  .dr-d:hover{background:#f0f2f4}
  .dr-d.mut{color:#cfd5da;cursor:default}.dr-d.mut:hover{background:transparent}
  .dr-d.empty{cursor:default}.dr-d.empty:hover{background:transparent}
  .dr-d.inrange{background:var(--soft);border-radius:0}
  .dr-d.sel{background:var(--red);color:#fff;font-weight:800}
  .dr-d.sel:hover{background:var(--red-d)}
  .dr-foot{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
  .dr-cancel{border:0;background:transparent;font-weight:700;color:var(--ink2);cursor:pointer;font-size:13px;padding:8px 14px;font-family:inherit}
  .dr-cancel:hover{color:var(--red)}
  .dr-apply{border:0;background:var(--red);color:#fff;font-weight:800;border-radius:9px;padding:8px 18px;cursor:pointer;font-size:13px;font-family:inherit}
  .dr-apply:hover{background:var(--red-d)}
  @media(max-width:640px){.dr-pop{width:330px}.dr-body{flex-direction:column}}

  .cmpbar{display:flex;align-items:center;justify-content:flex-end;gap:11px;margin-bottom:14px}
  .cmpbar .cmplab{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut);font-weight:700}
  .grid{display:grid;gap:14px}.kpis{grid-template-columns:repeat(3,1fr)}
  @media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr)}}
  .kpi .lab[title]{cursor:help;border-bottom:1px dotted #c9cfd4;display:inline-block}
  .card{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:17px 18px;box-shadow:0 1px 2px rgba(10,12,14,.03)}
  .kpi .lab{font-size:11.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut);font-weight:700}
  .kpi .val{font-size:26px;font-weight:800;letter-spacing:-.8px;margin-top:7px}
  .kpi .val.sm{font-size:20px}
  .kpi .yoy{font-size:12.5px;font-weight:700;margin-top:6px}
  .kpi .note{font-size:11.5px;color:var(--mut);margin-top:4px}
  .up{color:var(--good)}.down{color:var(--bad)}.star{color:var(--red)}
  .pending .val{color:#c2c9cf}
  .pill{display:inline-block;font-size:10.5px;font-weight:700;color:#fff;background:#aeb6bd;padding:2px 8px;border-radius:20px}

  section{margin-top:26px}
  .sec-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:13px;gap:12px;flex-wrap:wrap}
  .sec-h h2{font-size:16px;margin:0;font-weight:800;letter-spacing:-.3px}
  .sec-h .hint{color:var(--mut);font-size:12px}
  .row-ctrl{display:flex;gap:10px;align-items:center}
  .yr{font-size:12.5px;font-weight:700;border:1.5px solid var(--line);border-radius:9px;padding:6px 28px 6px 10px;background:#fff;cursor:pointer;font-family:inherit;color:var(--ink);
    -webkit-appearance:none;appearance:none;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237b848c' stroke-width='3'><path d='M6 9l6 6 6-6'/></svg>");
    background-repeat:no-repeat;background-position:right 9px center}
  .yr:hover{border-color:var(--red)}
  .msel{position:relative}
  .msel-btn{text-align:left;min-width:152px}
  .msel-pop{position:absolute;left:0;top:calc(100% + 6px);z-index:60;background:#fff;border:1px solid var(--line);border-radius:11px;box-shadow:0 14px 38px rgba(10,12,14,.16);padding:6px;width:240px}
  .msel-pop[hidden]{display:none}
  .msel-pop .hd{font-size:11px;color:var(--mut);font-weight:700;padding:6px 9px 4px}
  .msel-opt{display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600}
  .msel-opt:hover{background:#f4f6f8}
  .msel-opt input{accent-color:var(--red);width:15px;height:15px}
  .msel-opt.dis{opacity:.4;cursor:not-allowed}
  .msel-opt .dot{width:9px;height:9px;border-radius:50%;flex:none}
  .fsbtn{border:1.5px solid var(--line);background:#fff;color:var(--ink2);border-radius:9px;padding:6px 9px;cursor:pointer;display:inline-flex;align-items:center}
  .fsbtn:hover{border-color:var(--red);color:var(--red)}
  .chart-card{height:340px;position:relative}
  #trend{touch-action:pan-y}
  section.big #trend{touch-action:none}
  .tbackdrop{position:fixed;inset:0;background:rgba(10,12,14,.5);z-index:140}
  .tbackdrop[hidden]{display:none}
  section.big{position:fixed;left:12.5vw;top:12.5vh;width:75vw;height:75vh;margin:0;z-index:150;
    background:#fff;border-radius:16px;box-shadow:0 30px 80px rgba(0,0,0,.42);padding:16px 24px;display:flex;flex-direction:column}
  section.big .sec-h{flex:none}
  section.big .chart-card{flex:1;height:auto;min-height:0;border:0;box-shadow:none;padding:6px 0 0}
  .tabs{display:flex;gap:4px;background:rgba(255,255,255,.16);border-radius:11px;padding:4px}
  .tab{border:0;background:transparent;color:#e9ecee;font-weight:700;font-size:13px;padding:8px 15px;border-radius:8px;cursor:pointer;font-family:inherit}
  .tab:hover{color:#fff}.tab.on{background:#fff;color:var(--red)}
  .actsw{font-size:12.5px;font-weight:700;color:var(--ink2);display:inline-flex;align-items:center;gap:7px;cursor:pointer}
  .actsw input{accent-color:var(--red);width:15px;height:15px}
  .camp-name{font-weight:700;cursor:pointer;display:flex;align-items:center;gap:8px}
  .camp-name .caret{color:var(--mut);font-size:10px;display:inline-block;transition:transform .15s;width:9px;flex:none}
  .camp-name .cn-txt{flex:1;min-width:0;text-align:left}
  tr.cmp-open .caret{transform:rotate(90deg)}
  .badge{font-size:10px;font-weight:800;padding:2px 7px;border-radius:20px;white-space:nowrap}
  .badge.on{background:#e6f4ec;color:var(--good)}.badge.off{background:#eef0f2;color:var(--mut)}
  .plat-g{color:#2b6cb0;font-weight:700;font-size:11.5px}.plat-m{color:#7b3fa0;font-weight:700;font-size:11.5px}
  .crv-cell{padding:0!important;background:#fafbfc}
  .creatives{display:flex;gap:10px;flex-wrap:wrap;padding:11px 12px 15px}
  .crv{width:152px;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.05)}
  .crv img{width:100%;height:92px;object-fit:cover;display:block;background:#eef0f2}
  .crv .ct{padding:7px 9px}.crv .ct b{font-size:11.5px;display:block;line-height:1.3}
  .crv .ct p{font-size:10.5px;color:var(--mut);margin:3px 0 0;line-height:1.3;max-height:48px;overflow:hidden}
  .crv-a{text-decoration:none;color:inherit;cursor:pointer;transition:transform .12s,box-shadow .12s}
  .crv-a:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,190,212,.18);border-color:var(--red)}
  .crv-link{display:inline-block;margin-top:8px;font-size:10.5px;font-weight:800;color:#fff;background:var(--red);padding:4px 9px;border-radius:7px}
  .crv-a:hover .crv-link{background:var(--red-d)}
  .crv-note{padding:12px;color:var(--mut);font-size:12px}
  .gad-mock{margin:11px 12px;max-width:580px;border:1px solid var(--line);border-radius:11px;padding:13px 15px;background:#fff}
  .gad-top{display:flex;align-items:center;gap:9px}
  .gad-badge{font-size:11px;font-weight:800;color:#1a1a1a}
  .gad-url{font-size:12.5px;color:#0e8a3e}
  .gad-title{font-size:17px;color:#1a0dab;font-weight:600;margin-top:5px;line-height:1.25}
  .gad-desc{font-size:12.5px;color:#4d5156;margin-top:4px;line-height:1.4}
  .gad-actions{display:flex;gap:8px;flex-wrap:wrap;padding:4px 12px 14px}
  .gad-open{display:inline-block;font-size:11.5px;font-weight:800;color:#fff;background:var(--red);padding:7px 13px;border-radius:8px;text-decoration:none}
  .gad-open:hover{background:var(--red-d)}
  .gad-open.ghost{background:#fff;color:var(--ink2);border:1.5px solid var(--line)}
  .gad-open.ghost:hover{border-color:var(--red);color:var(--red)}
  #campBudget{margin-bottom:14px}
  .budgetcard{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:15px 20px}
  .budgetcard .bl{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut);font-weight:700;display:block}
  .budgetcard .bsub{font-size:12.5px;color:var(--ink2);font-weight:600;margin-top:4px;display:block}
  .budgetcard .bv{font-size:28px;font-weight:800;letter-spacing:-.8px;color:var(--red);white-space:nowrap}
  .budgetcard .bv small{font-size:14px;color:var(--mut);font-weight:700}

  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line)}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut);font-weight:700}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  th.sortable{cursor:pointer;user-select:none}
  th.sortable:hover{color:var(--red)}
  th.sorted{color:var(--red)}
  tbody tr:hover{background:#fbfcfd}
  .src{font-size:11px;color:var(--mut)}
  .tblwrap{max-height:520px;overflow:auto}
  .chan2{display:flex;flex-direction:column}
  .chrow{position:relative;display:grid;grid-template-columns:1.9fr 1fr .85fr .85fr;align-items:center;gap:6px;padding:9px 10px;border-bottom:1px solid var(--line);font-size:13px}
  .chrow .rb{position:absolute;left:0;top:4px;bottom:4px;width:calc(64% * var(--r));background:linear-gradient(90deg,#00bed4,#33b6c8);border-radius:7px;z-index:0}
  .chrow>span{position:relative;z-index:1;min-width:0}
  .chrow .cn{font-weight:700;color:#0a0c0e;text-shadow:0 0 3px #fff,0 0 5px #fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .chrow .num{text-align:right;font-variant-numeric:tabular-nums}
  .chrow .rev b{font-size:13.5px;text-shadow:0 0 3px #fff,0 0 5px #fff}
  .chrow.chhead{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut);font-weight:700}
  .chrow.chhead .num{color:var(--mut);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .chrow.chhead .hsm{display:none}
  .chrow.chfoot{font-weight:800;border-top:2px solid var(--line);border-bottom:0;background:#fcfcfd}

  .funnel{display:flex;flex-direction:column;gap:10px;padding:6px 2px}
  .fn-row{display:grid;grid-template-columns:152px minmax(0,1fr) 124px;align-items:center;gap:13px}
  .fn-side{min-width:0}
  .fn-lab{font-size:13.5px;font-weight:800;color:var(--ink);line-height:1.18}
  .fn-sub{font-size:11px;color:var(--mut);font-weight:600;margin-top:2px}
  .fn-track{position:relative;height:50px;display:flex;align-items:center}
  .fn-fill{height:100%;border-radius:11px;display:flex;align-items:center;padding:0 16px;color:#fff;
    min-width:74px;flex:none;transition:width .35s ease}
  .fn-fill b{font-size:21px;font-variant-numeric:tabular-nums;font-weight:800}
  .fn-cr{display:flex;flex-direction:column;justify-content:center;line-height:1.15;min-width:0}
  .fn-cr b{font-size:14px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
  .fn-crsub{font-size:10.5px;color:var(--mut);font-weight:600;margin-top:1px}

  .treemap{display:flex;flex-wrap:wrap;gap:6px}
  .tile{border-radius:11px;padding:11px 13px;color:#fff;display:flex;flex-direction:column;justify-content:space-between;min-height:74px;overflow:hidden;position:relative}
  .tile .bn{font-weight:800;font-size:14px}.tile .bv{font-size:12px;opacity:.92;font-weight:600;margin-top:3px}
  .tile .bs{position:absolute;right:10px;top:9px;font-size:11px;font-weight:800;opacity:.55}

  .bars{display:flex;flex-direction:column;gap:8px}
  .bar-row{display:grid;grid-template-columns:26px 1fr auto;align-items:center;gap:11px}
  .bar-row .rk{font-size:12px;font-weight:800;color:var(--mut);text-align:right}
  .bar-track{background:#f0f2f4;border-radius:8px;overflow:hidden;height:30px;position:relative;display:flex;align-items:center}
  .bar-fill{height:100%;background:linear-gradient(90deg,var(--red),#33b6c8);border-radius:8px;position:absolute;left:0;top:0}
  .bar-lbl{position:relative;padding-left:11px;font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;z-index:1;color:var(--ink)}
  .bar-row .vv{font-size:12.5px;font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap}
  .bar-row .vv small{color:var(--mut);font-weight:600}

  .two{grid-template-columns:1fr 1fr}@media(max-width:900px){.two{grid-template-columns:1fr}}
  .viewcard .vc-h{font-size:13px;font-weight:800;color:var(--ink);margin-bottom:12px;padding-bottom:9px;border-bottom:1px solid var(--line)}
  .viewcard.ga4 .vc-h{color:var(--red)}
  .vc-row{display:flex;align-items:baseline;justify-content:space-between;padding:7px 0}
  .vc-row span{font-size:12.5px;color:var(--mut);font-weight:600}
  .vc-row b{font-size:19px;font-weight:800;letter-spacing:-.4px;font-variant-numeric:tabular-nums}
  .vc-row.big{border-top:1px solid var(--line);margin-top:5px;padding-top:11px}
  .vc-row.big b{font-size:24px;color:var(--red)}
  .vc-row .yy{font-size:11.5px;font-weight:700;margin-left:8px}
  .vc-note{font-size:11px;color:var(--mut);margin-top:11px;line-height:1.35}
  .empty{color:var(--mut);font-size:13px;padding:20px;text-align:center;background:#fafbfc;border-radius:11px}
  .foot{color:var(--mut);font-size:11.5px;margin-top:40px;border-top:1px solid var(--line);padding-top:14px}
  @media(max-width:680px){
    .wrap{padding:16px 13px 60px}
    .hero-inner{padding:calc(15px + env(safe-area-inset-top,0px)) 13px 12px;gap:11px}
    .logo-img{height:28px}.logo-chip{padding:7px 10px}
    .tabs{order:3}
    .ctrl{width:100%;align-items:stretch}
    .dr-trigger{min-width:0;width:100%;font-size:13px;padding:9px 11px}
    .dr-pop{position:fixed;left:8px;right:8px;top:64px;width:auto}
    .pmeta{font-size:10.5px}
    .cmpbar{justify-content:space-between}
    .kpis{grid-template-columns:1fr 1fr;gap:10px}
    .card{padding:14px 14px}
    .kpi .val{font-size:22px}.kpi .val.sm{font-size:16px}
    section{margin-top:20px}
    .sec-h h2{font-size:15px}
    .row-ctrl{width:100%;flex-wrap:wrap;gap:7px}
    .fn-row{grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"lab lab" "bar cr";gap:5px 10px}
    .fn-side{grid-area:lab}.fn-track{grid-area:bar;height:42px}
    .fn-cr{grid-area:cr;align-items:flex-end}.fn-crsub{display:none}
    .fn-fill b{font-size:17px}.fn-cr b{font-size:13.5px}
    .chart-card{height:280px}
    section.big{left:0;top:0;width:100vw;height:100vh;height:100dvh;border-radius:0;padding:10px 12px}
    .tblwrap{overflow:visible;max-height:none}
    #campTbl thead{display:none}
    #campTbl table,#campTbl tbody,#campTbl tfoot{display:block;min-width:0}
    #campTbl tr.cmp,#campTbl tfoot tr{
      display:grid;grid-template-columns:1fr 1fr;gap:1px 14px;background:#fff;
      border:1px solid var(--line);border-radius:11px;margin:0 0 9px;padding:9px 13px}
    #campTbl tr.cmp td,#campTbl tfoot td{
      display:flex;justify-content:space-between;align-items:baseline;gap:8px;
      padding:4px 0;border:0;text-align:right;font-size:12.5px;min-width:0}
    #campTbl tr.cmp td::before,#campTbl tfoot td::before{
      content:attr(data-label);font-weight:700;color:var(--mut);font-size:10px;
      text-transform:uppercase;letter-spacing:.3px;text-align:left;white-space:nowrap;flex:none}
    #campTbl tr.cmp td:first-child,#campTbl tfoot td:first-child{
      grid-column:1/-1;justify-content:flex-start;font-weight:800;font-size:13.5px;
      padding-bottom:6px;margin-bottom:3px;border-bottom:1px solid var(--line)}
    #campTbl tr.cmp td:first-child::before,#campTbl tfoot td:first-child::before{display:none}
    #campTbl td.mhide{display:none}
    #campTbl tr.cmp:not(.cmp-open) td:nth-child(2),
    #campTbl tr.cmp:not(.cmp-open) td:nth-child(3),
    #campTbl tr.cmp:not(.cmp-open) td:nth-child(5),
    #campTbl tr.cmp:not(.cmp-open) td:nth-child(6){display:none}
    #campTbl tr.cmp .camp-name::after{content:"Detail";font-weight:700;font-size:9.5px;color:var(--red);
      text-transform:uppercase;letter-spacing:.4px;margin-left:auto;padding-left:8px;align-self:center}
    #campTbl tr.cmp.cmp-open .camp-name::after{content:"Zavrieť"}
    #campTbl tr.cmp td.num,#campTbl tfoot td.num{white-space:nowrap}
    #campTbl tr.cmp .camp-name{white-space:normal;width:100%}
    #campTbl tr.crv-row{display:block;margin:-7px 0 9px;border:1px solid var(--line);border-top:0;border-radius:0 0 11px 11px;background:#fafbfc}
    #campTbl tr.crv-row td{display:block;padding:0}
    .chrow{grid-template-columns:1.6fr 1fr .72fr .72fr;font-size:12px;padding:8px 9px;gap:6px}
    .chrow.chhead{letter-spacing:.2px;font-size:10px}
    .chrow.chhead .hfull{display:none}
    .chrow.chhead .hsm{display:inline}
    .chrow .rev b{font-size:12.5px}
    .treemap .tile{flex:1 1 44% !important}
    .budgetcard{flex-direction:column;align-items:flex-start;gap:8px}
    .budgetcard .bv{font-size:23px}
    .creatives .crv{width:46%}
  }
</style></head>
<body>
<header class="hero" id="topHeader">
  <div class="hero-inner">
    <div class="brand"><a class="logo-chip" href="#" id="logoHome" title="Domov reportu" onclick="goHome();return false;"><img class="logo-img" id="logoImg" alt="__BRAND__"></a></div>
    <nav class="tabs">
      <button class="tab on" data-tab="overview" type="button">Prehľad</button>
      <button class="tab" data-tab="campaigns" type="button">PPC kampane</button>
    </nav>
    <div class="ctrl">
      <div class="dr" id="dr">
        <button class="dr-trigger" id="drTrigger">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#00bed4" stroke-width="2"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/></svg>
          <span id="drLabel"></span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#7b848c" stroke-width="3"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <div class="dr-pop" id="drPop" hidden>
          <div class="dr-head"><select class="dr-preset" id="drPreset"></select></div>
          <div class="dr-body">
            <div class="dr-cal">
              <div class="dr-cap">Začiatok</div>
              <div class="dr-nav"><button data-nav="s-prev" type="button">‹</button><span id="capS"></span><button data-nav="s-next" type="button">›</button></div>
              <div class="dr-grid" id="gridS"></div>
            </div>
            <div class="dr-cal">
              <div class="dr-cap">Koniec</div>
              <div class="dr-nav"><button data-nav="e-prev" type="button">‹</button><span id="capE"></span><button data-nav="e-next" type="button">›</button></div>
              <div class="dr-grid" id="gridE"></div>
            </div>
          </div>
          <div class="dr-foot"><button class="dr-cancel" id="drCancel" type="button">Zrušiť</button><button class="dr-apply" id="drApply" type="button">Použiť</button></div>
        </div>
      </div>
      <div class="pmeta" id="pmeta"></div>
    </div>
  </div>
</header>

<div class="wrap">
<div id="tabOverview">
  <div class="cmpbar"><span class="cmplab">Porovnanie</span>
    <div class="toggle" style="display:inline-flex;background:#eef1f3;border-radius:10px;padding:3px">
      <button id="cmp-yoy" class="on" style="border:0;background:#fff;padding:6px 13px;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--red);cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.08)" onclick="setCmp('yoy')">YoY</button>
      <button id="cmp-mom" style="border:0;background:transparent;padding:6px 13px;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--ink2);cursor:pointer" onclick="setCmp('mom')">MoM</button></div></div>
  <div class="grid kpis" id="kpis"></div>

  <section id="viewsSec">
    <div class="sec-h"><div><h2>PPC spend a efektivita</h2>
      <div class="hint">Vybrané obdobie · leady spolu podľa akcie</div></div></div>
    <div class="grid two">
      <div class="card viewcard" id="viewPlatform"></div>
      <div class="card viewcard" id="viewGA4"></div>
    </div>
  </section>

  <section id="trendSec">
    <div class="sec-h"><div><h2>Výkonnosť v priebehu času</h2><div class="hint" id="trendhint"></div></div>
      <div class="row-ctrl">
        <div class="msel" id="msel">
          <button class="yr msel-btn" id="mselBtn" type="button">Leady spolu</button>
          <div class="msel-pop" id="mselPop" hidden></div>
        </div>
        <select class="yr" id="yr" onchange="drawTrend()"></select>
        <select class="yr" id="gran" onchange="setMode(this.value)">
          <option value="m">Mesačne</option>
          <option value="w">Týždenne</option>
          <option value="d">Denne</option>
        </select>
        <button class="fsbtn" id="rzbtn" onclick="resetZoom()" title="Reset priblíženia">Reset</button>
        <button class="fsbtn" id="fsbtn" onclick="toggleFs()" title="Na celú obrazovku">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg></button>
      </div></div>
    <div class="card chart-card" id="trendCard"><canvas id="trend"></canvas></div>
  </section>

  <section>
    <div class="sec-h"><div><h2>Leady podľa kanála (source / medium)</h2>
      <div class="hint">GA4, click_schedule_now + click_phone + click_mail · vybrané obdobie</div></div></div>
    <div class="card" id="channels"></div>
  </section>

  <section>
    <div class="sec-h"><div><h2>Leady podľa akcie</h2><div class="hint" id="catHint"></div></div></div>
    <div class="card"><div class="treemap" id="treemap"></div></div>
  </section>

</div><!-- /tabOverview -->

<div id="tabCampaigns" hidden>
  <section>
    <div class="sec-h"><div><h2>PPC kampane</h2><div class="hint" id="campHint"></div></div>
      <label class="actsw"><input type="checkbox" id="campActive"> len aktuálne spustené</label></div>
    <div id="campBudget"></div>
    <div class="card" style="padding:6px 6px"><div class="tblwrap"><div id="campTbl"></div></div></div>
  </section>

  <section>
    <div class="sec-h"><div><h2>Vyhľadávacie dopyty</h2><div class="hint" id="qHint">Google Ads, Search terms report</div></div></div>
    <div class="card" style="padding:6px 6px"><div class="tblwrap"><div id="qTbl"></div></div></div>
  </section>
</div>

  <div class="foot" id="foot"></div>
</div>
<div class="tbackdrop" id="tbackdrop" hidden></div>

<script>
const D=/*__DATA__*/;
const NB=" ";
const eur=(x,dec=0)=> x==null?"—":"$"+Number(x).toLocaleString("en-US",{minimumFractionDigits:dec,maximumFractionDigits:dec}).replace(/\s/g,NB);
const intf=x=> x==null?"—":Math.round(x).toLocaleString("en-US").replace(/\s/g,NB);
const SKM=["","jan","feb","mar","apr","máj","jún","júl","aug","sep","okt","nov","dec"];
const fmtD=s=>{const p=s.split("-");return `${+p[2]}.${+p[1]}.${p[0]}`;};
const pct=(c,p)=> (c==null||p==null||!p)?null:Math.round((c-p)/p*1000)/10;
const CATLAB={SCHEDULE:"Schedule now (klik)",PHONE:"Telefón (klik)",MAIL:"Email (klik)"};
let cmpMode='yoy';
const cmpLab=()=> cmpMode==='yoy'?'YoY':'MoM';
function yoyHtml(p,invert){ if(p==null) return `<span class="note">${cmpLab()} n/a</span>`;
  const good=invert?p<=0:p>=0; return `<span class="yoy ${good?'up':'down'}">${p>=0?'▲':'▼'} ${p>=0?'+':''}${p.toLocaleString('en-US')} % ${cmpLab()}</span>`; }
const shiftY=(s,n)=> (parseInt(s.slice(0,4))+n)+s.slice(4);
function rangeLen(F,T){return Math.round((new Date(T)-new Date(F))/864e5)+1;}
function prevRange(F,T){
  if(cmpMode==='yoy'){
    const a=parseK(F),b=parseK(T);
    // celý kalendárny mesiac/rok → YoY posun o kalendárny rok (tam je zarovnanie správne).
    // Inak (týždeň/deň/ľubovoľné okno) zarovnaj na DEŇ V TÝŽDNI: -364 dní = 52 týždňov,
    // nech KPI YoY sedí s týždenným trendom (ISO-week) a neporovnáva posunuté týždne.
    if(a.d===1 && b.d===lastDayOf(b.y,b.m)) return [shiftY(F,-1),shiftY(T,-1)];
    return [addDays(F,-364),addDays(T,-364)];
  }
  const a=parseK(F),b=parseK(T);
  if(a.d===1&&a.y===b.y&&a.m===b.m&&b.d===lastDayOf(b.y,b.m)){
    let y=a.y,m=a.m-1;if(m<0){m=11;y--;}return [keyOf(y,m,1),keyOf(y,m,lastDayOf(y,m))];}
  const pT=addDays(F,-1); return [addDays(pT,-(rangeLen(F,T)-1)),pT];}
function setCmp(m){cmpMode=m;
  document.getElementById('cmp-yoy').style.cssText=m==='yoy'?"border:0;background:#fff;padding:6px 13px;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--red);cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.08)":"border:0;background:transparent;padding:6px 13px;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--ink2);cursor:pointer";
  document.getElementById('cmp-mom').style.cssText=m==='mom'?"border:0;background:#fff;padding:6px 13px;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--red);cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.08)":"border:0;background:transparent;padding:6px 13px;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--ink2);cursor:pointer";
  render(curF,curT);}

if(D.logo) document.getElementById('logoImg').src=D.logo;
if(D.hero) document.getElementById('topHeader').style.backgroundImage="url('"+D.hero+"')";
const hasPPC=Object.keys(D.daily).length>0;

// ---- aggregations over [F,T] ----
function aggLeads(F,T){let leads=0,wf=0,rel=0,relMark=0,won=0,dealMark=0;const cats={},svcs={},svcWf={};
  for(const l of D.leads){if(l.d>=F&&l.d<=T){leads++;if(l.wf)wf++;cats[l.cat]=(cats[l.cat]||0)+1;
    const s=l.svc||'Neuvedené';svcs[s]=(svcs[s]||0)+1;if(l.wf)svcWf[s]=(svcWf[s]||0)+1;
    if('rel'in l){relMark++;if(l.rel)rel++;}
    if('obch'in l){dealMark++;if(l.obch==='won')won++;}}}
  return {leads,wf,cats,svcs,svcWf,rel,relMark,won,dealMark};}
function aggPPC(F,T){let cg=0,cm=0,vg=0,vm=0,has=false;
  for(const d in D.daily){if(d>=F&&d<=T){const x=D.daily[d];cg+=x.cost_gads;cm+=x.cost_meta;vg+=x.conv_gads||0;vm+=x.conv_meta||0;has=true;}}
  if(!has&&!hasPPC) return null;
  return {cost:cg+cm,cost_g:cg,cost_m:cm,conv:vg+vm};}
function channelsAgg(F,T){const by={};let ts=0,tl=0;
  for(const x of D.chan){if(x.d>=F&&x.d<=T){const k=x.sm||'(not set)';(by[k]=by[k]||{s:0,l:0});
    by[k].s+=x.s;by[k].l+=x.l;ts+=x.s;tl+=x.l;}}
  const rows=Object.entries(by).map(([name,v])=>({name,sessions:v.s,leads:v.l}))
    .sort((a,b)=>b.leads-a.leads||b.sessions-a.sessions).slice(0,15);
  return {rows,tot:{sessions:ts,leads:tl}};}
const PAID_MED=['cpc','ppc','paid','paidsearch','paid_social','cpm','display'];
function isPaidSM(sm){const med=((sm||'').split('/')[1]||'').trim().toLowerCase();return PAID_MED.some(k=>med.includes(k));}
function ga4PaidLeads(F,T){let l=0;for(const x of D.chan){if(x.d>=F&&x.d<=T&&isPaidSM(x.sm))l+=x.l;}return l;}
function yoyMini(p,invert){if(p==null)return'';const good=invert?p<=0:p>=0;return `<span class="yy ${good?'up':'down'}">${p>=0?'+':''}${p} % ${cmpLab()}</span>`;}
function renderViews(F,T,c,pc,p,pp){
  const plat=document.getElementById('viewPlatform'), g4=document.getElementById('viewGA4');
  if(!p){plat.className=g4.className="card viewcard";plat.innerHTML=g4.innerHTML='<div class="empty">Čaká na PPC dáta.</div>';return;}
  const cpa=c.leads?p.cost/c.leads:null, cpaP=(pp&&pc.leads)?pp.cost/pc.leads:null;
  plat.className="card viewcard";
  plat.innerHTML=`<div class="vc-h">CPA: Lead · leady spolu</div>
    <div class="vc-row"><span>PPC spend</span><b>${eur(p.cost)}</b></div>
    <div class="vc-row"><span>Leady spolu</span><b>${intf(c.leads)}</b></div>
    <div class="vc-row big"><span>CPA: Lead</span><b>${cpa!=null?eur(cpa,2):'—'} ${yoyMini(pct(cpa,cpaP),true)}</b></div>
    <div class="vc-note">CPA = PPC spend (Google Ads) / všetky leady (Schedule now + Phone + Mail).</div>`;
  g4.className="card viewcard ga4";
  const ce=Object.entries(c.cats).sort((a,b)=>b[1]-a[1]);
  g4.innerHTML=`<div class="vc-h">Leady podľa akcie</div>`+
    (ce.length?ce.map(([k,v])=>`<div class="vc-row"><span>${CATLAB[k]||k}</span><b>${intf(v)}</b></div>`).join(''):
      '<div class="vc-row"><span>Žiadne leady v tomto období</span></div>')+
    `<div class="vc-note">Rozpad ${intf(c.leads)} leadov podľa GTM click-akcie (GA4).</div>`;
}

const palette=["#00bed4","#0098ab","#33b6c8","#13889a","#1f9aad","#0d5e6a","#5cc6d4","#157d8d","#2aa5b8","#0f7280","#46b0c0","#0c6470","#6ad0dc","#198a99"];

// ---- KPI render for [F,T] ----
function render(F,T){
  const [pF,pT]=prevRange(F,T);
  const c=aggLeads(F,T), pr=aggLeads(pF,pT);
  document.getElementById('pmeta').textContent="vybrané: "+fmtD(F)+" – "+fmtD(T)+" · "+cmpLab()+" vs "+fmtD(pF)+" – "+fmtD(pT);
  const p=aggPPC(F,T), pp=aggPPC(pF,pT);
  const cards=[
    {lab:"Leady spolu",val:intf(c.leads),yoy:pct(c.leads,pr.leads),cls:"star"},
  ];
  if(p){
    const cpa=c.leads?p.cost/c.leads:null, cpaP=(pp&&pr.leads)?pp.cost/pr.leads:null;
    cards.push({lab:"PPC spend",val:eur(p.cost),yoy:pct(p.cost,pp?pp.cost:null),invert:true,note:"Google Ads"});
    cards.push({lab:"CPA: Lead",val:cpa!=null?eur(cpa,2):"—",yoy:pct(cpa,cpaP),invert:true});
  } else ["PPC spend","CPA: Lead"].forEach(l=>cards.push({lab:l,pending:true}));
  const kc=document.getElementById('kpis');kc.innerHTML='';
  cards.forEach(cd=>{const d=document.createElement('div');d.className="card kpi"+(cd.pending?" pending":"");
    if(cd.pending){d.innerHTML=`<div class="lab">${cd.lab}</div><div class="val">—</div><div class="note"><span class="pill">čaká na PPC dáta</span></div>`;}
    else{const yoy=cd.yoy!==undefined?yoyHtml(cd.yoy,cd.invert):(cd.note?`<span class="note">${cd.note}</span>`:"");
      const lab=`<div class="lab ${cd.cls||''}">${cd.lab}</div>`;
      d.innerHTML=`${lab}<div class="val ${cd.sm?'sm':''}">${cd.val}</div>${yoy||""}${(cd.note&&cd.yoy!==undefined)?`<div class="note">${cd.note}</div>`:""}`;}
    kc.appendChild(d);});
  renderViews(F,T,c,pr,p,pp);

  // channels: source/medium | leady | sessions
  const ch=document.getElementById('channels'); const ca=channelsAgg(F,T);
  if(ca.rows.length){const m0=ca.rows[0].leads||1;const ns=x=>x.toLocaleString('en-US').replace(/\s/g,NB);
    ch.innerHTML='<div class="chan2">'+
      '<div class="chrow chhead"><span>Source / Medium</span><span class="num">Leady</span><span class="num"><span class="hfull">Sessions</span><span class="hsm">Sess.</span></span><span class="num"><span class="hfull">CR</span><span class="hsm">CR</span></span></div>'+
      ca.rows.map(x=>{const cr=x.sessions?x.leads/x.sessions*100:0;return `<div class="chrow" style="--r:${(x.leads/m0).toFixed(4)}"><span class="rb"></span>
        <span class="cn">${x.name}</span><span class="num rev"><b>${intf(x.leads)}</b></span>
        <span class="num">${ns(x.sessions)}</span><span class="num">${cr.toFixed(1).replace('.',',')} %</span></div>`;}).join('')+
      `<div class="chrow chfoot"><span>Spolu</span><span class="num rev"><b>${intf(ca.tot.leads)}</b></span>
        <span class="num">${ns(ca.tot.sessions)}</span><span class="num">${ca.tot.sessions?(ca.tot.leads/ca.tot.sessions*100).toFixed(1).replace('.',','):'0'} %</span></div>`+
      '</div>';
  } else ch.innerHTML='<div class="empty">'+(hasPPC?'Žiadne GA4 dáta o kanáloch v tomto období.':'Čaká na GA4 dáta.')+'</div>';

  // kategórie leadov (treemap podľa podielu)
  const tm=document.getElementById('treemap');tm.innerHTML='';
  const ce=Object.entries(c.cats).map(([k,v])=>({k,v})).sort((a,b)=>b.v-a.v);
  const ct=ce.reduce((s,x)=>s+x.v,0)||1;
  document.getElementById('catHint').textContent=ce.length+" kategórií · "+intf(c.leads)+" leadov spolu";
  ce.forEach((b,i)=>{const sh=b.v/ct*100;const basis=Math.max(16,Math.sqrt(sh)*17);
    const d=document.createElement('div');d.className="tile";d.style.flex=`1 1 ${basis}%`;d.style.background=palette[i%palette.length];
    d.innerHTML=`<div class="bs">${sh.toFixed(0)}%</div><div class="bn">${CATLAB[b.k]||b.k}</div><div class="bv">${intf(b.v)} ${b.v===1?'lead':'leadov'}</div>`;tm.appendChild(d);});
  if(!ce.length)tm.innerHTML='<div class="empty">Žiadne leady v tomto období.</div>';
}

// ---- Trend: vybraná metrika, tento rok vs minulý rok ----
const SKMM=["Január","Február","Marec","Apríl","Máj","Jún","Júl","August","September","Október","November","December"];
const METRICS={
  leads:{label:"Leady spolu",fmt:"int"},
  cost:{label:"PPC spend",fmt:"eur"},
  cpa:{label:"CPA: Lead",fmt:"eur"},
};
function isoWeekKey(dstr){const t=new Date(Date.UTC(+dstr.slice(0,4),+dstr.slice(5,7)-1,+dstr.slice(8,10)));
  const dn=(t.getUTCDay()+6)%7; t.setUTCDate(t.getUTCDate()-dn+3);
  const ft=new Date(Date.UTC(t.getUTCFullYear(),0,4));
  const wk=1+Math.round((t-ft)/(7*864e5));
  return t.getUTCFullYear()+'-W'+String(wk).padStart(2,'0');}
function isoWeekMonday(y,w){const jan4=new Date(Date.UTC(y,0,4));const dn=(jan4.getUTCDay()+6)%7;
  const m=new Date(jan4); m.setUTCDate(jan4.getUTCDate()-dn+(w-1)*7); return m;}
// PPC naklad po mesiacoch / ISO tyzdnoch / dnoch (z dennych dat)
const ppcMonth={},ppcWeek={},ppcDay={};
for(const d in D.daily){const x=D.daily[d];const c=x.cost_gads+x.cost_meta;
  const mk=d.slice(0,7);(ppcMonth[mk]=ppcMonth[mk]||0);ppcMonth[mk]+=c;
  const wk=isoWeekKey(d);(ppcWeek[wk]=ppcWeek[wk]||0);ppcWeek[wk]+=c;
  ppcDay[d]=(ppcDay[d]||0)+c;}
// leady po mesiacoch / tyzdnoch / dnoch (z per-lead pola)
const leadMonth={},leadWeek={},leadDay={};
function addLead(o,l){o.l++;if(l.wf)o.w++;
  if('rel'in l){o.rm++;if(l.rel)o.r++;}              // rm=oznacene relevanciou, r=relevantne
  if('obch'in l){o.dm++;if(l.obch==='won')o.won++;}} // dm=uzavrete obchody, won=uspesne
const newB=()=>({l:0,w:0,r:0,rm:0,won:0,dm:0});
for(const l of D.leads){const mk=l.d.slice(0,7),wk=isoWeekKey(l.d);
  addLead(leadMonth[mk]=leadMonth[mk]||newB(),l);
  addLead(leadWeek[wk]=leadWeek[wk]||newB(),l);
  addLead(leadDay[l.d]=leadDay[l.d]||newB(),l);}
// mesacne pre trend: uprednostni oficialny Sumar (D.monthly), fallback raw leadMonth
function monthLeads(mk){const m=D.monthly[mk];if(m)return {l:m.leads,w:m.webform};return leadMonth[mk]||null;}
function metricVal(metric,scope,period){
  const lead=scope==='m'?monthLeads(period):scope==='w'?leadWeek[period]:leadDay[period];
  const cost=scope==='m'?ppcMonth[period]:scope==='w'?ppcWeek[period]:ppcDay[period];
  // relevancia/uspesnost su len v raw poli (Sumar ich nema) -> beri raw bucket aj pri mesiacoch
  const raw=scope==='m'?leadMonth[period]:scope==='w'?leadWeek[period]:leadDay[period];
  switch(metric){
    case 'leads':return lead?lead.l:null;
    case 'webform':return lead?lead.w:null;
    case 'cost':return cost!=null?cost:null;
    case 'cpa':return (cost!=null&&lead&&lead.l)?cost/lead.l:null;
    case 'cpl':return (cost!=null&&lead&&lead.w)?cost/lead.w:null;
    case 'wfshare':return (lead&&lead.l)?lead.w/lead.l*100:null;
    case 'relshare':return (raw&&raw.rm)?raw.r/raw.rm*100:null;
    case 'winshare':return (raw&&raw.dm)?raw.won/raw.dm*100:null;
  }
}
function fmtMetric(v,fmt){if(v==null)return"—";
  if(fmt==='eur')return eur(v,fmt==='eur'&&v<100?2:0);
  if(fmt==='pct')return v.toFixed(1).replace('.',',')+" %";
  return Math.round(v).toLocaleString('en-US').replace(/\s/g,NB);}

let mode='m';
let yManual=false;
function setMode(m){mode=m;const g=document.getElementById('gran');if(g)g.value=m;drawTrend();}
function autoFitY(){
  if(!trendChart||yManual)return;
  const xs=trendChart.scales.x,lo=xs.min,hi=xs.max,byAxis={};
  trendChart.data.datasets.forEach(ds=>{if(ds.hidden)return;const ax=ds.yAxisID||'y';
    ds.data.forEach(p=>{if(!p)return;const x=p.x,y=p.y;if(x==null||y==null)return;
      if(x<lo-0.5||x>hi+0.5)return;const a=byAxis[ax]||(byAxis[ax]={min:Infinity,max:-Infinity});
      if(y<a.min)a.min=y;if(y>a.max)a.max=y;});});
  let changed=false;
  for(const ax in byAxis){const a=byAxis[ax],s=trendChart.scales[ax];if(!s||!isFinite(a.min))continue;
    const pad=(a.max-a.min)*0.08||Math.abs(a.max)*0.08||1;
    s.options.min=Math.max(0,niceBound(a.min-pad,-1));s.options.max=niceBound(a.max+pad,1);changed=true;}
  if(changed)trendChart.update('none');
}
let trendChart=null;
let selMetrics=['leads'];
const fmtAxis=(v,fmt)=>{
  if(fmt==='eur'){const a=Math.abs(v);if(a>=10000)return '$'+Math.round(v/1000)+'k';if(a>=1000)return '$'+(Math.round(v/100)/10)+'k';return '$'+Math.round(v);}
  if(fmt==='pct')return (Math.round(v*10)/10)+' %';
  return Math.round(v).toLocaleString('en-US').replace(/\s/g,NB);
};
function niceBound(v,dir){if(!isFinite(v)||v===0)return 0;
  const mag=Math.pow(10,Math.floor(Math.log10(Math.abs(v))));const step=mag/2;
  return dir>0?Math.ceil(v/step)*step:Math.floor(v/step)*step;}
function trendPeriods(yr,py){const out=[];
  if(mode==='m'){for(let m=1;m<=12;m++){const mm=String(m).padStart(2,'0');
    out.push({idx:m,ck:`${yr}-${mm}`,pk:`${py}-${mm}`,label:SKM[m],title:SKMM[m-1]});}}
  else if(mode==='w'){for(let w=1;w<=53;w++){const ww=String(w).padStart(2,'0');
    const mon=isoWeekMonday(yr,w),sun=new Date(mon);sun.setUTCDate(mon.getUTCDate()+6);
    out.push({idx:w,ck:`${yr}-W${ww}`,pk:`${py}-W${ww}`,label:`${mon.getUTCDate()}.${mon.getUTCMonth()+1}.`,
      title:`${mon.getUTCDate()}.${mon.getUTCMonth()+1}. – ${sun.getUTCDate()}.${sun.getUTCMonth()+1}.${sun.getUTCFullYear()}`});}}
  else{const dim=((yr%4===0&&yr%100!==0)||yr%400===0)?366:365;
    for(let i=0;i<dim;i++){const cd=new Date(Date.UTC(yr,0,1+i)),pd=new Date(Date.UTC(py,0,1+i));
      out.push({idx:i+1,ck:cd.toISOString().slice(0,10),pk:pd.toISOString().slice(0,10),
        label:`${cd.getUTCDate()}.${cd.getUTCMonth()+1}.`,title:`${cd.getUTCDate()}.${cd.getUTCMonth()+1}.${yr}`});}}
  return out;}
const MCOLOR={leads:'#00bed4',webform:'#0e8a3e',cost:'#2b6cb0',cpa:'#d8743a',cpl:'#7b3fa0',wfshare:'#b8860b',relshare:'#2e9e5b',winshare:'#c0395b'};
function drawTrend(){
  const yr=+document.getElementById('yr').value, py=yr-1, scope=mode;
  const P=trendPeriods(yr,py), ms=selMetrics;
  const idxLabel={},idxTitle={}; P.forEach(p=>{idxLabel[p.idx]=p.label;idxTitle[p.idx]=p.title;});
  const lastIdx=P.length;
  yManual=false;
  let datasets;
  let scales={x:{type:'linear',min:1,max:lastIdx,grid:{display:false},
    ticks:{callback:v=>idxLabel[Math.round(v)]||'',font:{size:11},color:'#7b848c',maxRotation:0,autoSkip:true,maxTicksLimit:scope==='m'?12:13}}};
  if(ms.length===1){
    const m=ms[0], M=METRICS[m];
    document.getElementById('trendhint').textContent=`${M.label} · ${yr} vs ${py}`;
    datasets=[
      {label:String(yr),data:P.map(p=>({x:p.idx,y:metricVal(m,scope,p.ck)})),borderColor:'#00bed4',
        backgroundColor:'rgba(0,190,212,.10)',borderWidth:2.2,pointRadius:0,pointHoverRadius:4,tension:.25,fill:true,yAxisID:'y',spanGaps:true},
      {label:String(py),data:P.map(p=>({x:p.idx,y:metricVal(m,scope,p.pk)})),borderColor:'#c2c8ce',
        borderWidth:1.6,borderDash:[4,3],pointRadius:0,pointHoverRadius:4,tension:.25,fill:false,yAxisID:'y',spanGaps:true},
    ];
    scales.y={position:'left',grid:{color:'#eef1f3'},ticks:{callback:v=>fmtAxis(v,M.fmt),font:{size:11},color:'#7b848c'}};
  } else {
    document.getElementById('trendhint').textContent="Porovnanie metrík · "+ms.map(m=>METRICS[m].label).join(" · ")+" · "+yr;
    const axes=['y','y1','y2'];
    datasets=ms.map((m,i)=>({label:METRICS[m].label,data:P.map(p=>({x:p.idx,y:metricVal(m,scope,p.ck)})),
      borderColor:MCOLOR[m],backgroundColor:MCOLOR[m],borderWidth:2,pointRadius:0,pointHoverRadius:4,tension:.25,yAxisID:axes[i],fill:false,spanGaps:true}));
    ms.forEach((m,i)=>{scales[axes[i]]={type:'linear',position:i===0?'left':'right',display:i<2,
      grid:{display:i===0,color:'#eef1f3'},ticks:{callback:v=>fmtAxis(v,METRICS[m].fmt),color:MCOLOR[m],font:{size:11}}};});
  }
  const minRange=scope==='m'?1.5:scope==='w'?2:4;
  if(trendChart)trendChart.destroy();
  trendChart=new Chart(document.getElementById('trend'),{type:'line',data:{datasets},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false,axis:'x'},
      layout:{padding:{right:22}},animation:{duration:300},
      plugins:{legend:{labels:{boxWidth:12,font:{size:11.5},color:'#0a0c0e',usePointStyle:true}},
        tooltip:{callbacks:{title:items=>idxTitle[Math.round(items[0].parsed.x)]||'',
          label:c=>ms.length===1?`${METRICS[ms[0]].label} ${c.dataset.label}: ${fmtMetric(c.parsed.y,METRICS[ms[0]].fmt)}`:`${METRICS[ms[c.datasetIndex]].label}: ${fmtMetric(c.parsed.y,METRICS[ms[c.datasetIndex]].fmt)}`}},
        zoom:{
          pan:{enabled:true,mode:'x',threshold:5,onPan:autoFitY},
          zoom:{wheel:{enabled:true,speed:.12},pinch:{enabled:true},drag:{enabled:false},mode:'x',onZoom:autoFitY},
          limits:{x:{min:'original',max:'original',minRange:minRange}}
        }},
      scales}});
  autoFitY();
}
function resetZoom(){
  if(!trendChart)return;
  yManual=false;
  ['y','y1','y2'].forEach(k=>{const s=trendChart.scales[k];if(s){s.options.min=undefined;s.options.max=undefined;}});
  if(trendChart.resetZoom)trendChart.resetZoom('none');
  autoFitY();
}
(function(){const cv=document.getElementById('trend');if(!cv)return;
  let lastTap=0,sx=0,sy=0,st=0,multi=false;
  cv.addEventListener('touchstart',function(e){
    if(e.touches.length>1){multi=true;return;}
    multi=false;const t=e.touches[0];sx=t.clientX;sy=t.clientY;st=e.timeStamp;
  },{passive:true});
  cv.addEventListener('touchend',function(e){
    if(multi||e.touches.length>0)return;
    const ch=e.changedTouches[0],dt=e.timeStamp-st;
    const moved=Math.abs(ch.clientX-sx)+Math.abs(ch.clientY-sy);
    if(dt>250||moved>12){lastTap=0;return;}
    if(e.timeStamp-lastTap<320){resetZoom();e.preventDefault();lastTap=0;}
    else lastTap=e.timeStamp;
  },{passive:false});
  cv.addEventListener('dblclick',resetZoom);})();
(function(){const cv=document.getElementById('trend');if(!cv)return;
  function axisScalesAt(x){
    if(!trendChart||!trendChart.chartArea)return null;
    const a=trendChart.chartArea,S=trendChart.scales;
    let side=null; if(x<a.left)side='left'; else if(x>a.right)side='right';
    if(!side)return null;
    let out=['y','y1','y2'].map(k=>S[k]).filter(s=>s&&s.position===side);
    if(!out.length)out=['y','y1','y2'].map(k=>S[k]).filter(s=>s&&s.position==='left');
    return out.length?out:null;
  }
  function apply(snap,dy){
    yManual=true;
    const f=Math.min(5,Math.max(.2,Math.exp(dy/200)));
    snap.forEach(o=>{const span=(o.max-o.min)*f;o.s.options.min=o.min;o.s.options.max=o.min+span;});
    trendChart.update('none');
  }
  let on=false,sY=0,snap=[];
  cv.addEventListener('touchstart',function(e){
    if(e.touches.length!==1)return;
    const r=cv.getBoundingClientRect(),sc=axisScalesAt(e.touches[0].clientX-r.left);
    if(!sc)return; on=true;sY=e.touches[0].clientY;snap=sc.map(s=>({s,min:s.min,max:s.max}));
  },{passive:false});
  cv.addEventListener('touchmove',function(e){
    if(!on)return; e.preventDefault();e.stopPropagation();
    apply(snap,e.touches[0].clientY-sY);
  },{passive:false});
  function tend(){on=false;snap=[];}
  cv.addEventListener('touchend',tend);cv.addEventListener('touchcancel',tend);
  let mon=false,mY=0,msnap=[];
  cv.addEventListener('mousedown',function(e){
    const r=cv.getBoundingClientRect(),sc=axisScalesAt(e.clientX-r.left);
    if(!sc)return; mon=true;mY=e.clientY;msnap=sc.map(s=>({s,min:s.min,max:s.max}));e.preventDefault();
  });
  cv.addEventListener('mousemove',function(e){
    if(mon)return; const r=cv.getBoundingClientRect();
    cv.style.cursor=axisScalesAt(e.clientX-r.left)?'ns-resize':'';
  });
  window.addEventListener('mousemove',function(e){if(mon)apply(msnap,e.clientY-mY);});
  window.addEventListener('mouseup',function(){mon=false;msnap=[];});
})();
function setBig(on){const sec=document.getElementById('trendSec'),bd=document.getElementById('tbackdrop');
  sec.classList.toggle('big',on);bd.hidden=!on;
  document.getElementById('fsbtn').title=on?"Zmenšiť":"Zväčšiť";
  if(trendChart){requestAnimationFrame(()=>{trendChart.resize();
    setTimeout(()=>trendChart.resize(),200);});}}
function toggleFs(){setBig(!document.getElementById('trendSec').classList.contains('big'));}
document.getElementById('tbackdrop').addEventListener('click',()=>setBig(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape')setBig(false);});

// ---- Looker-style date range picker ----
const DMAX=D.date_max, Ymax=+DMAX.slice(0,4), Mmax=+DMAX.slice(5,7);
const MINK=D.list_since+"-01";
const SKFULL=["Január","Február","Marec","Apríl","Máj","Jún","Júl","August","September","Október","November","December"];
const WD=["Po","Ut","St","Št","Pi","So","Ne"];
const pad=n=>String(n).padStart(2,'0');
const keyOf=(y,m,d)=>`${y}-${pad(m+1)}-${pad(d)}`;
const parseK=s=>({y:+s.slice(0,4),m:+s.slice(5,7)-1,d:+s.slice(8,10)});
const lastDayOf=(y,m)=>new Date(y,m+1,0).getDate();
function addDays(s,n){const p=parseK(s);const d=new Date(p.y,p.m,p.d+n);return keyOf(d.getFullYear(),d.getMonth(),d.getDate());}
function lastCompleteMonth(){let y=Ymax,m=Mmax-2;if(m<0){m=11;y--;}return [keyOf(y,m,1),keyOf(y,m,lastDayOf(y,m))];}
const GEN=D.generated||DMAX;
const DEND=(function(){let y=GEN<=DMAX?GEN:DMAX;if(y<MINK)y=DMAX;return y;})();
function defaultRange(){const sy=+DEND.slice(0,4),sm=+DEND.slice(5,7)-1;return [keyOf(sy,sm,1),DEND];}
const PRE={
  "Minulý mesiac":()=>lastCompleteMonth(),
  "Tento mesiac":()=>defaultRange(),
  "Tento rok":()=>[keyOf(+DEND.slice(0,4),0,1),DEND],
  "Posledných 30 dní":()=>[addDays(DEND,-29),DEND],
  "Posledných 90 dní":()=>[addDays(DEND,-89),DEND],
  "Posledných 12 mesiacov":()=>{const e=parseK(DEND);let y=e.y-1,m=e.m;return [keyOf(y,m,1),DEND];},
};
const $=id=>document.getElementById(id);
function labelOf(F,T){const a=parseK(F),b=parseK(T);return `${a.d}. ${SKM[a.m+1]} ${a.y} – ${b.d}. ${SKM[b.m+1]} ${b.y}`;}
function setLabel(F,T){$('drLabel').textContent=labelOf(F,T);}

let curF,curT,tmpF,tmpT,viewS,viewE;
const monthOf=s=>{const p=parseK(s);return {y:p.y,m:p.m};};
function shiftView(v,delta){v.m+=delta;if(v.m<0){v.m=11;v.y--;}else if(v.m>11){v.m=0;v.y++;}}
function gridHTML(view){
  let h=WD.map(w=>`<div class="dr-wd">${w}</div>`).join('');
  const lead=(new Date(view.y,view.m,1).getDay()+6)%7;
  for(let i=0;i<lead;i++)h+='<div class="dr-d empty"></div>';
  for(let d=1;d<=lastDayOf(view.y,view.m);d++){const k=keyOf(view.y,view.m,d);let c="dr-d";
    if(k<MINK||k>DMAX)c+=" mut";
    else{if(k===tmpF||k===tmpT)c+=" sel";else if(k>tmpF&&k<tmpT)c+=" inrange";}
    h+=`<div class="${c}" data-k="${k}">${d}</div>`;}
  return h;
}
function refreshCals(){
  $('capS').textContent=`${SKFULL[viewS.m]} ${viewS.y}`.toUpperCase();
  $('capE').textContent=`${SKFULL[viewE.m]} ${viewE.y}`.toUpperCase();
  $('gridS').innerHTML=gridHTML(viewS); $('gridE').innerHTML=gridHTML(viewE);
}
function matchPreset(){let f="Vlastný";for(const n in PRE){const [a,b]=PRE[n]();if(a===tmpF&&b===tmpT){f=n;break;}}$('drPreset').value=f;}
function openPop(){tmpF=curF;tmpT=curT;viewS=monthOf(curF);viewE=monthOf(curT);matchPreset();refreshCals();$('drPop').hidden=false;}
function closePop(){$('drPop').hidden=true;}

const ps=$('drPreset');
["Vlastný",...Object.keys(PRE)].forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n;ps.appendChild(o);});
ps.addEventListener('change',()=>{const n=ps.value;if(PRE[n]){const [f,t]=PRE[n]();tmpF=f;tmpT=t;viewS=monthOf(f);viewE=monthOf(t);refreshCals();}});
$('gridS').addEventListener('click',e=>{const k=e.target.dataset.k;if(!k||k<MINK||k>DMAX)return;tmpF=k;if(tmpF>tmpT)tmpT=tmpF;ps.value="Vlastný";refreshCals();});
$('gridE').addEventListener('click',e=>{const k=e.target.dataset.k;if(!k||k<MINK||k>DMAX)return;tmpT=k;if(tmpT<tmpF)tmpF=tmpT;ps.value="Vlastný";refreshCals();});
$('drPop').addEventListener('click',e=>{e.stopPropagation();const nav=e.target.dataset.nav;if(!nav)return;
  shiftView(nav[0]==='s'?viewS:viewE, nav.endsWith('prev')?-1:1);refreshCals();});
$('drApply').addEventListener('click',()=>{curF=tmpF;curT=tmpT;setLabel(curF,curT);render(curF,curT);
  if(!document.getElementById('tabCampaigns').hidden)renderCampaigns(curF,curT);closePop();});
$('drCancel').addEventListener('click',closePop);
$('drTrigger').addEventListener('click',e=>{e.stopPropagation();$('drPop').hidden?openPop():closePop();});
document.addEventListener('click',()=>{if(!$('drPop').hidden)closePop();});

// metric multi-select (max 3)
const MAXM=3;
const mselBtn=document.getElementById('mselBtn'), mselPop=document.getElementById('mselPop');
function updateMselLabel(){mselBtn.textContent=selMetrics.length===1?METRICS[selMetrics[0]].label:selMetrics.length+" metriky";}
function renderMselOptions(){
  mselPop.innerHTML='<div class="hd">Vyber max '+MAXM+' metriky</div>'+
    Object.entries(METRICS).map(([k,m])=>{const ch=selMetrics.includes(k);const dis=!ch&&selMetrics.length>=MAXM;
      return `<label class="msel-opt${dis?' dis':''}"><input type="checkbox" value="${k}" ${ch?'checked':''} ${dis?'disabled':''}>
        <span class="dot" style="background:${MCOLOR[k]}"></span>${m.label}</label>`;}).join('');
  mselPop.querySelectorAll('input').forEach(inp=>inp.addEventListener('change',()=>{const v=inp.value;
    if(inp.checked){if(!selMetrics.includes(v)){if(selMetrics.length>=MAXM)return;selMetrics.push(v);}}
    else{if(selMetrics.length<=1)return;selMetrics=selMetrics.filter(x=>x!==v);}
    updateMselLabel();renderMselOptions();drawTrend();}));
}
mselBtn.addEventListener('click',e=>{e.stopPropagation();mselPop.hidden=!mselPop.hidden;});
mselPop.addEventListener('click',e=>e.stopPropagation());
document.addEventListener('click',()=>{mselPop.hidden=true;});
renderMselOptions();updateMselLabel();
const yrSel=document.getElementById('yr');
const years=[...new Set(Object.keys(D.monthly).map(k=>k.slice(0,4)))].filter(y=>y>="2024").sort().reverse();
years.forEach(y=>{const o=document.createElement('option');o.value=y;o.textContent=`${y} vs ${+y-1}`;yrSel.appendChild(o);});
yrSel.value=String(Ymax);

// ---- PPC kampane (tab) ----
let campSort={col:'co',dir:-1};
function campAgg(F,T){const by={};
  for(const r of D.camp_daily){if(r.d>=F&&r.d<=T){const b=(by[r.cid]=by[r.cid]||{co:0,cl:0,im:0,cv:0});
    b.co+=r.co;b.cl+=r.cl;b.im+=r.im;b.cv+=r.cv;}}
  return by;}
function renderCampaigns(F,T){
  const agg=campAgg(F,T), activeOnly=document.getElementById('campActive').checked;
  let rows=Object.entries(agg).map(([cid,m])=>{const c=D.campaigns[cid]||{name:cid,status:'',plat:''};
      return {cid,...m,name:c.name,status:c.status,plat:c.plat};}).filter(r=>r.co>0);
  if(activeOnly) rows=rows.filter(r=>['ENABLED','ACTIVE'].includes(r.status));
  rows.forEach(r=>{r.ctr=r.im?r.cl/r.im*100:0;r.cpc=r.cl?r.co/r.cl:0;r.cpl=r.cv?r.co/r.cv:null;});
  rows.sort((a,b)=>{if(campSort.col==='name')return campSort.dir*String(a.name).localeCompare(String(b.name),'sk');
    const av=a[campSort.col]==null?-Infinity:a[campSort.col],bv=b[campSort.col]==null?-Infinity:b[campSort.col];
    return campSort.dir*(av-bv);});
  const w=D.camp_window||{};
  document.getElementById('campHint').textContent=rows.length+" kampaní · "+fmtD(F)+" – "+fmtD(T)+(w.start?" · história od "+fmtD(w.start):"");
  const b=D.budgets||{};
  document.getElementById('campBudget').innerHTML=b.total?`<div class="card budgetcard">
    <div><span class="bl">Aktuálny denný budget · ${b.count||0} reálne zobrazovaných kampaní</span>
      <span class="bsub">Google Ads ${eur(b.gads)} · Meta ${eur(b.meta)} · len kampane s impresiami za posl. 7 dní</span></div>
    <span class="bv">${eur(b.total)}<small> /deň</small></span></div>`:'';
  const el=document.getElementById('campTbl');
  if(!rows.length){el.innerHTML='<div class="empty">Žiadne kampane v tomto období.</div>';return;}
  const COLS=[{k:'name',l:'Kampaň'},{l:'Platforma'},{l:'Stav'},{k:'co',l:'Investícia',n:1},{k:'cl',l:'Kliknutia',n:1},
    {k:'ctr',l:'CTR',n:1},{k:'cpc',l:'CPC',n:1},{k:'cv',l:'Leady',n:1},{k:'cpl',l:'CPA',n:1}];
  const thead=COLS.map(c=>{const act=c.k&&c.k===campSort.col;const ind=act?(campSort.dir<0?' ▾':' ▴'):'';
    return `<th class="${c.n?'num ':''}${c.k?'sortable':''}${act?' sorted':''}"${c.k?` data-sort="${c.k}"`:''}>${c.l}${ind}</th>`;}).join('');
  el.innerHTML='<table><thead><tr>'+thead+'</tr></thead><tbody>'+
    rows.map(r=>{const on=['ENABLED','ACTIVE'].includes(r.status);
      return `<tr class="cmp" data-cid="${r.cid}"><td data-label="Kampaň"><div class="camp-name"><span class="caret">▶</span><span class="cn-txt">${r.name}</span></div></td>
        <td data-label="Platforma"><span class="plat-${r.plat==='Meta'?'m':'g'}">${r.plat}</span></td>
        <td data-label="Stav"><span class="badge ${on?'on':'off'}">${on?'aktívna':'pozastav.'}</span></td>
        <td class="num" data-label="Investícia">${eur(r.co)}</td><td class="num" data-label="Kliknutia">${r.cl.toLocaleString('en-US').replace(/\s/g,NB)}</td>
        <td class="num" data-label="CTR">${r.ctr.toFixed(2).replace('.',',')} %</td><td class="num" data-label="CPC">${eur(r.cpc,2)}</td>
        <td class="num" data-label="Leady"><b>${intf(r.cv)}</b></td><td class="num" data-label="CPA">${r.cpl!=null?eur(r.cpl,2):'—'}</td></tr>`;}).join('')
    +'</tbody>'+(()=>{const T2=rows.reduce((a,r)=>{a.co+=r.co;a.cl+=r.cl;a.im+=r.im;a.cv+=r.cv;return a;},{co:0,cl:0,im:0,cv:0});
      const tctr=T2.im?T2.cl/T2.im*100:0,tcpc=T2.cl?T2.co/T2.cl:0,tcpl=T2.cv?T2.co/T2.cv:null;
      return `<tfoot><tr><td data-label="Kampaň">Spolu (${rows.length})</td><td class="mhide"></td><td class="mhide"></td>
        <td class="num" data-label="Investícia">${eur(T2.co)}</td><td class="num" data-label="Kliknutia">${T2.cl.toLocaleString('en-US').replace(/\s/g,NB)}</td>
        <td class="num" data-label="CTR">${tctr.toFixed(2).replace('.',',')} %</td><td class="num" data-label="CPC">${eur(tcpc,2)}</td>
        <td class="num" data-label="Leady"><b>${intf(T2.cv)}</b></td><td class="num" data-label="CPA">${tcpl!=null?eur(tcpl,2):'—'}</td></tr></tfoot>`;})()
    +'</table>';
  el.querySelectorAll('tr.cmp').forEach(tr=>tr.querySelector('.camp-name').addEventListener('click',()=>toggleCreatives(tr)));
  el.querySelectorAll('th.sortable').forEach(th=>th.addEventListener('click',()=>{const col=th.dataset.sort;
    if(campSort.col===col)campSort.dir*=-1; else campSort={col,dir:col==='name'?1:-1};
    renderCampaigns(F,T);}));
}
let qRendered=false;
function renderSearchTerms(){
  if(qRendered)return; qRendered=true;
  const rows=(D.searchTerms||[]).map(r=>({...r,ctr:r.im?r.cl/r.im*100:0,cpc:r.cl?r.co/r.cl:0}));
  const w=D.searchTermsWindow||{};
  document.getElementById('qHint').textContent=(rows.length?rows.length+' dopytov · ':'')+'Google Ads'+
    (w.start?' · '+fmtD(w.start)+' – '+fmtD(w.end):'');
  const el=document.getElementById('qTbl');
  if(!rows.length){el.innerHTML='<div class="empty">Žiadne vyhľadávacie dopyty v tomto období.</div>';return;}
  el.innerHTML='<table><thead><tr><th>Dopyt</th><th class="num">Zobrazenia</th><th class="num">Kliknutia</th>'+
    '<th class="num">CTR</th><th class="num">Cena</th><th class="num">Leady</th></tr></thead><tbody>'+
    rows.map(r=>`<tr><td data-label="Dopyt">${r.term}</td>
      <td class="num" data-label="Zobrazenia">${r.im.toLocaleString('en-US').replace(/\s/g,NB)}</td>
      <td class="num" data-label="Kliknutia">${r.cl.toLocaleString('en-US').replace(/\s/g,NB)}</td>
      <td class="num" data-label="CTR">${r.ctr.toFixed(2).replace('.',',')} %</td>
      <td class="num" data-label="Cena">${eur(r.co,2)}</td>
      <td class="num" data-label="Leady"><b>${intf(r.cv)}</b></td></tr>`).join('')
    +'</tbody></table>';
}
function creativesHTML(cid){
  if(cid[0]==='m'){const ads=D.creatives[cid];
    if(!ads||!ads.length)return '<div class="crv-note">Pre túto Meta kampaň nie sú dostupné náhľady aktívnych reklám.</div>';
    return '<div class="creatives">'+ads.map(a=>{const inner=`${a.thumb?`<img src="${a.thumb}" loading="lazy" onerror="this.style.display='none'">`:''}
      <div class="ct"><b>${a.title||a.name||''}</b><p>${(a.body||'').slice(0,130)}</p>${a.link?'<span class="crv-link">Náhľad reklamy na Facebooku</span>':''}</div>`;
      return a.link?`<a class="crv crv-a" href="${a.link}" target="_blank" rel="noopener">${inner}</a>`:`<div class="crv">${inner}</div>`;}).join('')+'</div>';
  } else {const rs=D.rsa[cid];
    const land=(rs&&rs[0]&&rs[0].url)?rs[0].url:'';
    let body;
    if(rs&&rs.length)
      body=rs.map(a=>{let dom='';try{dom=new URL(a.url||'').hostname.replace('www.','');}catch(e){}
        return `<div class="gad-mock"><div class="gad-top"><span class="gad-badge">Reklama</span><span class="gad-url">${dom}</span></div>
          <div class="gad-title">${(a.heads||[]).slice(0,3).join(' | ')}</div>
          <div class="gad-desc">${(a.descs||[]).join(' ')}</div></div>`;}).join('');
    else body='<div class="crv-note">Vizuálny náhľad nie je dostupný.</div>';
    return body+(land?`<div class="gad-actions"><a class="gad-open ghost" href="${land}" target="_blank" rel="noopener">Cieľová stránka</a></div>`:'');
  }
}
function toggleCreatives(tr){const nx=tr.nextElementSibling;
  if(nx&&nx.classList.contains('crv-row')){nx.remove();tr.classList.remove('cmp-open');return;}
  tr.classList.add('cmp-open');const row=document.createElement('tr');row.className='crv-row';
  const cell=document.createElement('td');cell.colSpan=9;cell.className='crv-cell';cell.innerHTML=creativesHTML(tr.dataset.cid);
  row.appendChild(cell);tr.after(row);}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===b));
  const t=b.dataset.tab;
  document.getElementById('tabOverview').hidden=(t!=='overview');
  document.getElementById('tabCampaigns').hidden=(t!=='campaigns');
  if(t==='campaigns'){renderCampaigns(curF,curT);renderSearchTerms();}
}));
document.getElementById('campActive').addEventListener('change',()=>renderCampaigns(curF,curT));

function goHome(){
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x.dataset.tab==='overview'));
  document.getElementById('tabOverview').hidden=false;
  document.getElementById('tabCampaigns').hidden=true;
  const [f,t]=defaultRange();curF=f;curT=t;setLabel(f,t);render(f,t);drawTrend();
  window.scrollTo({top:0,behavior:'smooth'});
}

// init
const [F0,T0]=defaultRange();curF=F0;curT=T0;setLabel(F0,T0);render(F0,T0);drawTrend();
</script>
</body></html>
"""

if __name__=="__main__":
    main()
