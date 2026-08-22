import os
import json
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

def main():
    print("=== 1. Стадии основной воронки сделок ===")
    stages = call_b24("crm.dealcategory.stage.list", {"id": 0})
    if "result" in stages:
        for st in stages["result"]:
            print(f"  - [{st.get('STATUS_ID')}] {st.get('NAME')} (семантика: {st.get('SEMANTICS', 'P')})")
    else:
        print(stages)

    print("\n=== 2. Товары в последней сделке 41900 ===")
    rows = call_b24("crm.deal.productrows.get", {"id": 41900})
    print(json.dumps(rows, indent=2, ensure_ascii=False))

    print("\n=== 3. Сводка по UTM_SOURCE за последние 100 сделок ===")
    recent_deals = call_b24("crm.deal.list", {
        "order": {"DATE_CREATE": "DESC"},
        "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "UTM_SOURCE", "UTM_CAMPAIGN", "DATE_CREATE"],
        "start": 0
    })
    
    utm_counts = {}
    total_sum = 0
    if "result" in recent_deals:
        for d in recent_deals["result"]:
            source = d.get("UTM_SOURCE") or "Органика/Без UTM"
            opp = float(d.get("OPPORTUNITY") or 0)
            total_sum += opp
            if source not in utm_counts:
                utm_counts[source] = {"count": 0, "sum": 0.0}
            utm_counts[source]["count"] += 1
            utm_counts[source]["sum"] += opp

        print(f"Обработано последних сделок: {len(recent_deals['result'])}, на сумму: {total_sum:,.2f} ₽")
        print("Распределение по рекламным источникам (UTM_SOURCE):")
        for src, stat in sorted(utm_counts.items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"  • {src}: {stat['count']} сделок | {stat['sum']:,.2f} ₽")

if __name__ == "__main__":
    main()
