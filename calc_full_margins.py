import re
import csv

# We read the full CSV pasted by user
with open("sales_margin_full.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Всего строк в таблице продаж: {len(rows)}")

def clean_num(val):
    if not val:
        return 0.0
    val = val.replace(" ", "").replace(" ", "").replace(",", ".").replace("\"", "").replace("₽", "").strip()
    try:
        return float(val)
    except:
        return 0.0

def categorize(name):
    n = name.lower()
    if "ошибка" in n or not n.strip():
        return "Не определено / Ошибка"
    
    # 1. Пылесосы и умный дом
    if any(k in n for k in ["пылесос", "dreame", "roborock", "очиститель"]):
        return "Роботы и пылесосы"
    if any(k in n for k in ["dyson", "стайлер", "фен", "выпрямитель", "airstrait", "airwrap", "corrale", "supersonic"]):
        return "Dyson / Красота"
    
    # 2. Ноутбуки и компьютеры
    if any(k in n for k in ["macbook", "mac mini", "mac studio", "imac"]):
        if "air" in n or "neo" in n:
            return "MacBook Air & Neo"
        elif "pro" in n or "studio" in n or "imac" in n:
            return "MacBook Pro / Studio / iMac"
        return "Apple Mac"
    if any(k in n for k in ["matebook", "asus", "tecno", "hp laptop", "surface laptop", "ноутбук"]):
        return "Ноутбуки Windows & Huawei"
        
    # 3. Телевизоры и Мониторы
    if any(k in n for k in ["телевизор", "studio display", "монитор"]):
        return "Телевизоры и Мониторы"
        
    # 4. Планшеты
    if "ipad" in n:
        if "pro" in n:
            return "Apple iPad Pro"
        elif "air" in n:
            return "Apple iPad Air"
        elif "mini" in n:
            return "Apple iPad Mini"
        return "Apple iPad Base"
    if any(k in n for k in ["tab s", "pad 7", "pad 8", "redmi pad", "matepad", "surface pro", "poco pad"]):
        return "Планшеты Android & Win (MatePad / Tab / Poco)"
        
    # 5. Смартфоны
    if "iphone" in n:
        if "pro max" in n or "promax" in n:
            return "Apple iPhone Pro Max"
        elif "pro" in n:
            return "Apple iPhone Pro"
        elif "air" in n:
            return "Apple iPhone Air"
        elif "plus" in n:
            return "Apple iPhone Plus"
        else:
            return "Apple iPhone Base / e"
            
    if any(k in n for k in ["galaxy s26", "galaxy s25", "galaxy s24", "fold", "flip"]):
        return "Samsung Флагманы (S-серия, Fold, Flip)"
    if any(k in n for k in ["galaxy a", "galaxy m"]):
        return "Samsung A-серия (Масс-маркет)"
    if any(k in n for k in ["xiaomi 17", "xiaomi 15", "xiaomi 14", "pura 90", "pura 80", "pura 70", "magic 8", "magic v", "find n", "pixel 10", "pixel 9", "oneplus 15", "oneplus 13", "x300", "mate 80", "mate xt"]):
        return "Android Флагманы (Xiaomi Ultra, Pura, Magic, Pixel, OnePlus)"
    if any(k in n for k in ["poco", "redmi", "nord", "nova", "honor 400", "honor 600", "cmf phone", "nothing phone", "15t", "14t", "17t"]):
        return "Android Масс-маркет & Субфлагманы (Poco, Redmi, Honor, 14T/15T)"

    # 6. Часы и носимые
    if "apple watch" in n:
        if "ultra" in n:
            return "Apple Watch Ultra"
        return "Apple Watch Series & SE"
    if any(k in n for k in ["garmin", "whoop", "huawei watch", "galaxy watch", "oura", "fitbit"]):
        return "Смарт-часы non-Apple (Garmin, Huawei, Whoop)"
        
    # 7. Наушники и аудио
    if "airpods max" in n:
        return "Apple AirPods Max"
    if any(k in n for k in ["airpods", "earpods"]):
        return "Apple AirPods TWS & EarPods"
    if any(k in n for k in ["marshall", "b&w", "bowers", "sony wh", "freebuds", "beats", "jbl", "harman", "buds"]):
        return "Наушники & Акустика non-Apple (Marshall, Sony, B&W)"
    if any(k in n for k in ["станция", "яндекс"]):
        return "Умные колонки (Яндекс Станции)"
        
    # 8. Гаджеты, камеры, консоли
    if any(k in n for k in ["ray-ban", "ray ban", "очки", "oakley"]):
        return "Умные очки (Ray-Ban Meta, Oakley)"
    if any(k in n for k in ["dji", "osmo", "gopro", "insta360", "квадрокоптер", "микрофон dji", "canon"]):
        return "Фото/Видео (DJI, GoPro, Insta360, Canon)"
    if any(k in n for k in ["playstation", "ps5", "nintendo", "switch", "steam deck", "vr2", "quest", "xbox"]):
        return "Игровые консоли & VR (PS5, Switch, Steam Deck, Quest)"
    if any(k in n for k in ["plaud", "диктофон"]):
        return "AI-гаджеты (Plaud Note)"
    if any(k in n for k in ["pencil", "клавиатура", "keyboard", "чехол", "зарядка", "стилус"]):
        return "Аксессуары (Pencil, Magic Keyboard, Зарядки)"
        
    return "Прочая техника"

cat_stats = {}
total_rev = 0
total_profit = 0

for r in rows:
    name = r.get("Наименование", "")
    cat = categorize(name)
    price = clean_num(r.get("Цена в Б24", "0"))
    cost = clean_num(r.get("Цена закупки", "0"))
    profit = clean_num(r.get("ЧП", "0"))
    if profit == 0 and price > 0 and cost > 0:
        profit = price - cost
    qty = clean_num(r.get("Кол-во товара", "1")) or 1
    
    if price == 0:
        continue
        
    total_rev += price
    total_profit += profit

    if cat not in cat_stats:
        cat_stats[cat] = {"count": 0, "rev": 0.0, "profit": 0.0}
    cat_stats[cat]["count"] += int(qty)
    cat_stats[cat]["rev"] += price
    cat_stats[cat]["profit"] += profit

print(f"ИТОГО: Выручка: {total_rev:,.0f} ₽ | Чистая прибыль: {total_profit:,.0f} ₽ | Маржа: {(total_profit/total_rev)*100:.1f}%\n")
print(f"{'Категория':45s} | {'Штук':4s} | {'ЧП (Прибыль)':12s} | {'Маржа, %':8s} | {'Прибыль/шт':11s} | {'Выручка':12s}")
print("-" * 105)
for cat, s in sorted(cat_stats.items(), key=lambda x: x[1]['profit'], reverse=True):
    margin_pct = (s['profit'] / s['rev']) * 100 if s['rev'] > 0 else 0
    profit_per_item = s['profit'] / s['count'] if s['count'] > 0 else 0
    print(f"{cat:45s} | {s['count']:4d} | {s['profit']:11,.0f} ₽ | {margin_pct:7.1f}% | {profit_per_item:9,.0f} ₽ | {s['rev']:11,.0f} ₽")
