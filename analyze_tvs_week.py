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
    data = json.dumps(params or {}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

def main():
    # 1. Fetch stage names
    stages_raw = call_b24("crm.dealcategory.stage.list", {"id": 0})
    stages_map = {s["STATUS_ID"]: s["NAME"] for s in stages_raw.get("result", [])}

    # 2. Fetch all deals since Monday 17.08.2026
    deals = []
    start = 0
    while True:
        res = call_b24("crm.deal.list", {
            "order": {"DATE_CREATE": "ASC"},
            "filter": {">=DATE_CREATE": "2026-08-17T00:00:00+03:00"},
            "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_CREATE", "UTM_SOURCE", "UTM_CAMPAIGN", "UTM_MEDIUM", "SOURCE_ID"],
            "start": start
        })
        items = res.get("result", [])
        deals.extend(items)
        if "next" in res:
            start = res["next"]
        else:
            break

    print(f"Всего сделок в CRM за неделю (17-21 авг): {len(deals)}")

    # 3. For each deal, fetch product rows to identify TV deals
    tv_deals = []
    tv_keywords = ["телевизор", "tv", "oled", "qled", "hisense", "haier", "tcl"]

    for d in deals:
        did = d["ID"]
        prows = call_b24("crm.deal.productrows.get", {"id": did})
        products = prows.get("result", [])
        
        is_tv = False
        tv_products = []
        for p in products:
            p_name = p.get("PRODUCT_NAME", "").lower()
            if any(k in p_name for k in ["телевизор", "тв ", "tv "]) or ("hisense" in p_name and any(x in p_name for x in ['"', 'дюйм', 'u7', 'u8', 'a6', 'e7'])) or ("tcl" in p_name and any(x in p_name for x in ['"', 'c6', 'c7', 'c8', 'p6', 'p7'])) or ("haier" in p_name and any(x in p_name for x in ['"', 'smart tv', 'hqled'])):
                is_tv = True
                tv_products.append(p)
        
        # Also check title
        if not is_tv:
            title_lower = d.get("TITLE", "").lower()
            if "телевизор" in title_lower:
                is_tv = True

        if is_tv:
            d["tv_products"] = tv_products
            tv_deals.append(d)

    print(f"\nНайдено заказов по Телевизорам за неделю: {len(tv_deals)}")

    # Group by Stage
    stage_counts = {}
    stage_sums = {}
    brand_stats = {}
    total_tv_sum = 0.0
    won_tv_sum = 0.0
    won_count = 0

    for td in tv_deals:
        st_id = td.get("STAGE_ID")
        st_name = stages_map.get(st_id, st_id)
        opp = float(td.get("OPPORTUNITY") or 0)
        total_tv_sum += opp

        stage_counts[st_name] = stage_counts.get(st_name, 0) + 1
        stage_sums[st_name] = stage_sums.get(st_name, 0.0) + opp

        if st_id == "WON":
            won_count += 1
            won_tv_sum += opp

        # Identify brands
        prod_names = " ".join([p.get("PRODUCT_NAME", "") for p in td.get("tv_products", [])])
        brand = "Другие / Не указан"
        for b in ["Hisense", "Samsung", "LG", "TCL", "Haier", "Xiaomi"]:
            if b.lower() in prod_names.lower():
                brand = b
                break
        
        if brand not in brand_stats:
            brand_stats[brand] = {"total": 0, "won": 0, "lose": 0, "in_work": 0, "sum": 0.0}
        brand_stats[brand]["total"] += 1
        brand_stats[brand]["sum"] += opp
        if st_id == "WON":
            brand_stats[brand]["won"] += 1
        elif st_id in ["LOSE", "APOLOGY", "UC_RRQO4D", "UC_OL2S30", "UC_LWROSL", "UC_IVB3AA", "UC_3JZ3IX", "UC_I3TUCW", "UC_2VQFLC", "1", "2", "3", "4", "5", "6"]:
            brand_stats[brand]["lose"] += 1
        else:
            brand_stats[brand]["in_work"] += 1

    print(f"Общая сумма заказов на ТВ: {total_tv_sum:,.2f} ₽")
    print(f"Выкуплено (WON): {won_count} заказов на сумму {won_tv_sum:,.2f} ₽\n")

    print("=== 1. РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ ===")
    for st_name, cnt in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
        s_sum = stage_sums[st_name]
        pct = (cnt / len(tv_deals)) * 100
        print(f"• {st_name:48s}: {cnt:2d} заказов ({pct:4.1f}%) | {s_sum:10,.0f} ₽")

    print("\n=== 2. СРЕЗ ПО БРЕНДАМ ТЕЛЕВИЗОРОВ ===")
    for b, s in sorted(brand_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"• Бренд {b:10s} | Всего: {s['total']:2d} ({s['sum']:10,.0f} ₽) | Выкуплено: {s['won']} | Отказы: {s['lose']} | В работе: {s['in_work']}")

    print("\n=== 3. СПИСОК ВСЕХ СДЕЛОК ПО ТВ ЗА НЕДЕЛЮ ===")
    for td in tv_deals:
        st_id = td.get("STAGE_ID")
        st_name = stages_map.get(st_id, st_id)
        opp = float(td.get("OPPORTUNITY") or 0)
        p_names = ", ".join([p.get("PRODUCT_NAME", "") for p in td.get("tv_products", [])])
        print(f"ID {td['ID']} | {td['DATE_CREATE'][:10]} | {opp:9,.0f} ₽ | Статус: {st_name:30s} | UTM: {str(td.get('UTM_SOURCE')):10s} | {p_names}")

if __name__ == "__main__":
    main()
