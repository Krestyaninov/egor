import os
import json
import csv
import io
from datetime import datetime
import urllib.request

# Чтение .env
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
if not WEBHOOK_URL.endswith('/'):
    WEBHOOK_URL += '/'

def call_b24(method: str, params: dict = None):
    url = f"{WEBHOOK_URL}{method}.json"
    data = None
    if params:
        data = json.dumps(params).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

def fetch_deals_since(date_from="2026-08-11"):
    all_deals = []
    start = 0
    while True:
        res = call_b24("crm.deal.list", {
            "order": {"DATE_CREATE": "DESC"},
            "filter": {">=DATE_CREATE": f"{date_from}T00:00:00+03:00"},
            "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_CREATE", "UTM_SOURCE", "UTM_CAMPAIGN", "UTM_MEDIUM", "SOURCE_ID", "PROBABILITY"],
            "start": start
        })
        items = res.get("result", [])
        all_deals.extend(items)
        if "next" in res:
            start = res["next"]
        else:
            break
    return all_deals

def main():
    print("Fetching deals from Bitrix24...")
    deals = fetch_deals_since("2026-08-11")
    print(f"Total deals fetched since 11.08.2026: {len(deals)}")

    # Group by Date
    daily_stats = {}
    stage_stats = {}
    
    for d in deals:
        d_create = d.get("DATE_CREATE", "")[:10]
        st = d.get("STAGE_ID")
        opp = float(d.get("OPPORTUNITY") or 0)
        
        if d_create not in daily_stats:
            daily_stats[d_create] = {"count": 0, "sum": 0.0, "won_count": 0, "won_sum": 0.0, "lose_count": 0, "lose_sum": 0.0, "stages": {}}
        
        daily_stats[d_create]["count"] += 1
        daily_stats[d_create]["sum"] += opp
        
        if st == "WON":
            daily_stats[d_create]["won_count"] += 1
            daily_stats[d_create]["won_sum"] += opp
        elif st in ["LOSE", "APOLOGY", "UC_RRQO4D", "UC_OL2S30", "UC_LWROSL", "UC_IVB3AA", "UC_3JZ3IX", "UC_I3TUCW", "UC_2VQFLC", "1", "2", "3", "4", "5", "6"]:
            daily_stats[d_create]["lose_count"] += 1
            daily_stats[d_create]["lose_sum"] += opp
        
        daily_stats[d_create]["stages"][st] = daily_stats[d_create]["stages"].get(st, 0) + 1

    print("\n--- Daily Deals Dynamics ---")
    for d_day in sorted(daily_stats.keys()):
        stat = daily_stats[d_day]
        print(f"Date: {d_day} | Total Deals: {stat['count']:3d} ({stat['sum']:10,.0f} ₽) | WON: {stat['won_count']:2d} ({stat['won_sum']:10,.0f} ₽) | REJECTED: {stat['lose_count']:2d} | IN WORK: {stat['count'] - stat['won_count'] - stat['lose_count']:2d}")

    # Stage breakdown for last 3 days (19, 20, 21 Aug) vs previous days (14-18 Aug)
    print("\n--- Stage Breakdown (Recent 3 days: 19-21 Aug) ---")
    recent_stages = {}
    prev_stages = {}
    for d in deals:
        d_create = d.get("DATE_CREATE", "")[:10]
        st = d.get("STAGE_ID")
        if d_create in ["2026-08-19", "2026-08-20", "2026-08-21"]:
            recent_stages[st] = recent_stages.get(st, 0) + 1
        elif d_create in ["2026-08-14", "2026-08-15", "2026-08-16", "2026-08-17", "2026-08-18"]:
            prev_stages[st] = prev_stages.get(st, 0) + 1

    print("Recent (19-21 Aug):", recent_stages)
    print("Prev (14-18 Aug):", prev_stages)

if __name__ == "__main__":
    main()
