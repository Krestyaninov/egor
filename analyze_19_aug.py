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
    # 1. Fetch stage names
    stages_raw = call_b24("crm.dealcategory.stage.list", {"id": 0})
    stages_map = {s["STATUS_ID"]: s["NAME"] for s in stages_raw.get("result", [])}

    # 2. Fetch all deals created on 19.08.2026
    deals_19 = []
    start = 0
    while True:
        res = call_b24("crm.deal.list", {
            "order": {"ID": "ASC"},
            "filter": {
                ">=DATE_CREATE": "2026-08-19T00:00:00+03:00",
                "<=DATE_CREATE": "2026-08-19T23:59:59+03:00"
            },
            "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_CREATE", "UTM_SOURCE", "UTM_CAMPAIGN", "SOURCE_ID"],
            "start": start
        })
        items = res.get("result", [])
        deals_19.extend(items)
        if "next" in res:
            start = res["next"]
        else:
            break

    print(f"Всего заказов за 19.08.2026: {len(deals_19)}")

    # 3. Group by stage
    stages_summary = {}
    stage_deals = {}
    total_sum = 0.0

    for d in deals_19:
        st_id = d.get("STAGE_ID")
        st_name = stages_map.get(st_id, st_id)
        opp = float(d.get("OPPORTUNITY") or 0)
        total_sum += opp

        if st_name not in stages_summary:
            stages_summary[st_name] = {"count": 0, "sum": 0.0}
            stage_deals[st_name] = []

        stages_summary[st_name]["count"] += 1
        stages_summary[st_name]["sum"] += opp
        stage_deals[st_name].append(d)

    print(f"Общая сумма заказов: {total_sum:,.2f} ₽\n")
    print("=== РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ ЗА 19.08.2026 ===")
    for st_name, stat in sorted(stages_summary.items(), key=lambda x: x[1]['count'], reverse=True):
        pct = (stat['count'] / len(deals_19)) * 100
        print(f"• {st_name:48s}: {stat['count']:2d} шт ({pct:4.1f}%) | {stat['sum']:10,.0f} ₽")

    print("\n=== ДЕТАЛИЗАЦИЯ ПО ОСНОВНЫМ СТАТУСАМ ===")
    for st_name in ["Заказ выкуплен", "Взят в работу 3-7 дней", "Взят в работу до 3-х дней", "Неактуально", "Нет в наличии", "Не устроила цена", "Нет товара в наличии (клиент ждет поступления)"]:
        if st_name in stage_deals:
            print(f"\n--- Статус: {st_name} ({len(stage_deals[st_name])} сделок) ---")
            for d in stage_deals[st_name][:5]:
                print(f"  ID {d['ID']}: {d['TITLE']} | {float(d.get('OPPORTUNITY') or 0):,.0f} ₽ | UTM: {d.get('UTM_SOURCE')} | Источник: {d.get('SOURCE_ID')}")

if __name__ == "__main__":
    main()
