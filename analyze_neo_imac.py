import csv
import urllib.request
import json
import os

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

# 1. Analyze historical margin data for Neo and iMac
with open("complete_sales_data.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

def clean_num(val):
    if not val:
        return 0.0
    val = val.replace(" ", "").replace(" ", "").replace(",", ".").replace("\"", "").replace("₽", "").strip()
    try:
        return float(val)
    except:
        return 0.0

neo_sales = []
imac_sales = []

for r in rows:
    name = r.get("Наименование", "")
    n = name.lower()
    price = clean_num(r.get("Цена в Б24", "0"))
    cost = clean_num(r.get("Цена закупки", "0"))
    profit = clean_num(r.get("ЧП", "0"))
    if profit == 0 and price > 0 and cost > 0:
        profit = price - cost
    
    if "neo" in n:
        r["clean_price"] = price
        r["clean_profit"] = profit
        r["margin_pct"] = (profit / price * 100) if price > 0 else 0
        neo_sales.append(r)
    elif "imac" in n or "моноблок" in n:
        r["clean_price"] = price
        r["clean_profit"] = profit
        r["margin_pct"] = (profit / price * 100) if price > 0 else 0
        imac_sales.append(r)

print("=== 1. ИСТОРИЯ ПРОДАЖ: MACBOOK NEO ===")
print(f"Всего продаж Neo в выборке: {len(neo_sales)}")
neo_rev = sum(x["clean_price"] for x in neo_sales)
neo_profit = sum(x["clean_profit"] for x in neo_sales)
print(f"Выручка: {neo_rev:,.0f} ₽ | ЧП: {neo_profit:,.0f} ₽ | Ср. маржа: {(neo_profit/neo_rev)*100:.1f}% | Ср. ЧП/шт: {neo_profit/len(neo_sales):,.0f} ₽" if neo_sales else "0")
for x in neo_sales:
    print(f"  {x['Дата создания заказа']} | {x['clean_price']:6,.0f} ₽ | ЧП: {x['clean_profit']:5,.0f} ₽ ({x['margin_pct']:4.1f}%) | {x['Наименование']}")

print("\n=== 2. ИСТОРИЯ ПРОДАЖ: APPLE IMAC (МОНОБЛОКИ) ===")
print(f"Всего продаж iMac в выборке: {len(imac_sales)}")
imac_rev = sum(x["clean_price"] for x in imac_sales)
imac_profit = sum(x["clean_profit"] for x in imac_sales)
print(f"Выручка: {imac_rev:,.0f} ₽ | ЧП: {imac_profit:,.0f} ₽ | Ср. маржа: {(imac_profit/imac_rev)*100:.1f}% | Ср. ЧП/шт: {imac_profit/len(imac_sales):,.0f} ₽" if imac_sales else "0")
for x in imac_sales:
    print(f"  {x['Дата создания заказа']} | {x['clean_price']:6,.0f} ₽ | ЧП: {x['clean_profit']:5,.0f} ₽ ({x['margin_pct']:4.1f}%) | {x['Наименование']}")

# 2. Search CRM for Neo and iMac in recent deals
print("\n=== 3. ПОИСК СДЕЛОК В CRM ПО NEO И IMAC (за последний месяц) ===")
res = call_b24("crm.deal.list", {
    "order": {"DATE_CREATE": "DESC"},
    "filter": {">=DATE_CREATE": "2026-07-20T00:00:00+03:00"},
    "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "DATE_CREATE", "UTM_SOURCE"],
    "start": 0
})
stages_raw = call_b24("crm.dealcategory.stage.list", {"id": 0})
stages_map = {s["STATUS_ID"]: s["NAME"] for s in stages_raw.get("result", [])}

crm_deals = res.get("result", [])
print(f"Проверено недавних сделок в CRM: {len(crm_deals)}")
neo_crm = []
imac_crm = []

for d in crm_deals:
    did = d["ID"]
    prows = call_b24("crm.deal.productrows.get", {"id": did})
    products = prows.get("result", [])
    for p in products:
        pn = p.get("PRODUCT_NAME", "").lower()
        if "neo" in pn:
            d["product_name"] = p.get("PRODUCT_NAME")
            neo_crm.append(d)
        elif "imac" in pn or "моноблок" in pn:
            d["product_name"] = p.get("PRODUCT_NAME")
            imac_crm.append(d)

print(f"Найдено в CRM сделок по Neo: {len(neo_crm)}")
for d in neo_crm:
    st_name = stages_map.get(d["STAGE_ID"], d["STAGE_ID"])
    print(f"  ID {d['ID']} | {d['DATE_CREATE'][:10]} | {float(d.get('OPPORTUNITY') or 0):,.0f} ₽ | {st_name} | UTM: {d.get('UTM_SOURCE')} | {d.get('product_name')}")

print(f"\nНайдено в CRM сделок по iMac: {len(imac_crm)}")
for d in imac_crm:
    st_name = stages_map.get(d["STAGE_ID"], d["STAGE_ID"])
    print(f"  ID {d['ID']} | {d['DATE_CREATE'][:10]} | {float(d.get('OPPORTUNITY') or 0):,.0f} ₽ | {st_name} | UTM: {d.get('UTM_SOURCE')} | {d.get('product_name')}")
