import csv

# We read complete_sales_data.csv and filter specific product groups
with open("complete_sales_data.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

def clean_num(val):
    if not val:
        return 0.0
    val = val.replace(" ", "").replace(" ", "").replace(",", ".").replace("\"", "").replace("₽", "").strip()
    try:
        return float(val)
    except:
        return 0.0

groups = {
    "iPad Base": [],
    "iPad Air": [],
    "iPad Pro": [],
    "iPad Mini": [],
    "Apple Watch": [],
    "AirPods": [],
    "Garmin": [],
    "Dyson / Beauty": [],
    "Marshall": [],
}

for r in rows:
    name = r.get("Наименование", "").lower()
    price = clean_num(r.get("Цена в Б24", "0"))
    cost = clean_num(r.get("Цена закупки", "0"))
    profit = clean_num(r.get("ЧП", "0"))
    if profit == 0 and price > 0 and cost > 0:
        profit = price - cost
    r["price"] = price
    r["profit"] = profit
    
    if "ipad" in name:
        if "pro" in name:
            groups["iPad Pro"].append(r)
        elif "air" in name:
            groups["iPad Air"].append(r)
        elif "mini" in name:
            groups["iPad Mini"].append(r)
        else:
            groups["iPad Base"].append(r)
    elif "apple watch" in name:
        groups["Apple Watch"].append(r)
    elif "airpods" in name:
        groups["AirPods"].append(r)
    elif "garmin" in name:
        groups["Garmin"].append(r)
    elif any(k in name for k in ["dyson", "airwrap", "supersonic", "airstrait", "corrale"]):
        groups["Dyson / Beauty"].append(r)
    elif "marshall" in name:
        groups["Marshall"].append(r)

print("=== ДЕТАЛЬНАЯ МАРЖИНАЛЬНОСТЬ И ПРОДАЖИ ===")
for g, items in groups.items():
    if not items:
        continue
    cnt = len(items)
    tot_rev = sum(x["price"] for x in items)
    tot_prof = sum(x["profit"] for x in items)
    avg_chk = tot_rev / cnt if cnt > 0 else 0
    avg_prof = tot_prof / cnt if cnt > 0 else 0
    margin = (tot_prof / tot_rev * 100) if tot_rev > 0 else 0
    print(f"{g:16s} | Продаж: {cnt:2d} шт | ЧП всего: {tot_prof:8,.0f} ₽ | Ср. ЧП/шт: {avg_prof:6,.0f} ₽ | Маржа: {margin:5.1f}% | Ср. чек: {avg_chk:7,.0f} ₽")
