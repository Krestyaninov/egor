import os
import json
import urllib.request
from datetime import datetime

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

def main():
    # Fetch stages names
    stages_raw = call_b24("crm.dealcategory.stage.list", {"id": 0})
    stages_map = {s["STATUS_ID"]: s["NAME"] for s in stages_raw.get("result", [])}

    # Fetch recent deals (18-21 Aug)
    res = call_b24("crm.deal.list", {
        "order": {"DATE_CREATE": "DESC"},
        "filter": {">=DATE_CREATE": "2026-08-18T00:00:00+03:00"},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "DATE_CREATE", "UTM_SOURCE", "UTM_CAMPAIGN"],
        "start": 0
    })
    deals = res.get("result", [])
    print(f"Total deals 18-21 Aug: {len(deals)}")

    reasons = {}
    for d in deals:
        st = d.get("STAGE_ID")
        st_name = stages_map.get(st, st)
        opp = float(d.get("OPPORTUNITY") or 0)
        reasons[st_name] = reasons.get(st_name, 0) + 1

    print("\n=== РАСПРЕДЕЛЕНИЕ СТАДИЙ (18-21 АВГУСТА) ===")
    for st_name, cnt in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"  {st_name:50s}: {cnt:2d} сделок")

if __name__ == "__main__":
    main()
