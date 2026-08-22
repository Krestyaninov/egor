from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from config import STAGE_MAP, CATEGORY_MARGIN_BENCHMARKS
from b24_client import b24

# МСК таймзона (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    return datetime.now(MSK_TZ)

def classify_product(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["dyson", "airwrap", "supersonic", "airstrait", "corrale", "фен", "стайлер"]):
        return "Dyson / Красота"
    elif any(k in n for k in ["dreame", "roborock", "пылесос", "робот-пылесос", "x40", "l30", "qrevo"]):
        return "Роботы и пылесосы"
    elif any(k in n for k in ["телевизор", "hisense", "oled", "qled", "mini-led", "55\"", "65\"", "75\"", "85\"", "100\""]):
        return "Телевизоры"
    elif "macbook" in n or "mac mini" in n or "mac studio" in n or "imac" in n:
        if "pro" in n or "studio" in n or "imac" in n:
            return "MacBook Pro / Studio"
        else:
            return "MacBook Air & Neo"
    elif "ipad" in n:
        return "Apple iPad"
    elif "apple watch" in n or "garmin" in n:
        return "Apple Watch / Garmin"
    elif any(k in n for k in ["airpods", "marshall", "beats", "наушники", "акустика", "jbl"]):
        return "Наушники / Акустика"
    elif any(k in n for k in ["playstation", "ps5", "nintendo", "switch", "quest", "vr", "steam deck"]):
        return "Игровые приставки / VR"
    elif any(k in n for k in ["ray-ban", "умные очки", "очки meta", "oura"]):
        return "Умные очки / Гаджеты"
    elif any(k in n for k in ["iphone", "айфон"]):
        return "Apple iPhone"
    elif any(k in n for k in ["ultra", "pura", "magic", "fold", "flip", "s25", "s26", "oneplus 13", "oneplus 15", "pixel"]):
        return "Android Флагманы"
    elif any(k in n for k in ["poco", "redmi", "galaxy a", "honor", "14t", "15t", "nothing"]):
        return "Android Масс-маркет"
    else:
        return "Прочее"

async def get_funnel_summary(start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    """Сбор и расчет точной сквозной воронки продаж для маркетинга"""
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00+03:00")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59+03:00")
    
    deals = await b24.get_deals_by_date(start_str, end_str)
    
    total_count = len(deals)
    total_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in deals)
    
    # 1. Мусор / Спам / Дубли
    junk_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "JUNK"]
    junk_count = len(junk_deals)
    junk_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in junk_deals)
    
    # 2. Квалифицированные лиды
    qual_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") != "JUNK"]
    qual_count = len(qual_deals)
    qual_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in qual_deals)
    qual_rate = (qual_count / total_count * 100) if total_count > 0 else 0.0
    
    # 3. Выкуп (WON)
    won_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "WON"]
    won_count = len(won_deals)
    won_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in won_deals)
    
    # 4. В работе / Пайплайн
    in_work_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "IN_WORK"]
    in_work_count = len(in_work_deals)
    in_work_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in in_work_deals)
    
    # Детализация стадий в работе
    in_work_breakdown = {}
    for d in in_work_deals:
        st = d.get("STAGE_ID", "")
        name = STAGE_MAP.get(st, {}).get("name", st)
        amt = float(d.get("OPPORTUNITY") or 0)
        if name not in in_work_breakdown:
            in_work_breakdown[name] = {"count": 0, "amount": 0.0}
        in_work_breakdown[name]["count"] += 1
        in_work_breakdown[name]["amount"] += amt

    # 5. Квалифицированные отказы
    lose_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "LOSE"]
    lose_count = len(lose_deals)
    lose_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in lose_deals)
    
    # Причины отказов с суммами
    reasons_stat = {}
    for d in lose_deals:
        st = d.get("STAGE_ID", "")
        st_name = STAGE_MAP.get(st, {}).get("name", f"Отказ ({st})")
        amt = float(d.get("OPPORTUNITY") or 0)
        if st_name not in reasons_stat:
            reasons_stat[st_name] = {"count": 0, "amount": 0.0}
        reasons_stat[st_name]["count"] += 1
        reasons_stat[st_name]["amount"] += amt
        
    # Конверсия в выкуп от квалифицированных лидов
    cr_qual = (won_count / qual_count * 100) if qual_count > 0 else 0.0
    
    return {
        "start_dt": start_dt,
        "end_dt": end_dt,
        "total_count": total_count,
        "total_amount": total_amount,
        "junk_count": junk_count,
        "junk_amount": junk_amount,
        "qual_count": qual_count,
        "qual_amount": qual_amount,
        "qual_rate": qual_rate,
        "won_count": won_count,
        "won_amount": won_amount,
        "cr_qual": cr_qual,
        "in_work_count": in_work_count,
        "in_work_amount": in_work_amount,
        "in_work_breakdown": sorted(in_work_breakdown.items(), key=lambda x: x[1]["amount"], reverse=True),
        "lose_count": lose_count,
        "lose_amount": lose_amount,
        "reasons": sorted(reasons_stat.items(), key=lambda x: x[1]["amount"], reverse=True),
        "deals": deals,
        "won_deals": won_deals
    }

async def get_categories_breakdown(won_deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Детальный расчет маржинальности и выручки по категориям для выкупленных заказов"""
    categories = {}
    
    for d in won_deals:
        amt = float(d.get("OPPORTUNITY") or 0)
        title = d.get("TITLE", "")
        cat_name = classify_product(title)
        
        # Получаем маржинальный бенчмарк для категории
        margin_pct = CATEGORY_MARGIN_BENCHMARKS.get(cat_name, 0.07)
        profit = amt * margin_pct
        
        if cat_name not in categories:
            categories[cat_name] = {
                "category": cat_name,
                "count": 0,
                "revenue": 0.0,
                "profit": 0.0,
                "margin_pct": margin_pct * 100
            }
        categories[cat_name]["count"] += 1
        categories[cat_name]["revenue"] += amt
        categories[cat_name]["profit"] += profit
        
    result = list(categories.values())
    result.sort(key=lambda x: x["profit"], reverse=True)
    return result

async def get_pipeline_stuck_deals() -> List[Dict[str, Any]]:
    """Поиск сделок, зависших в статусах ожидания или без движения"""
    now = get_now_msk()
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00+03:00")
    
    deals = await b24.get_deals_by_date(week_ago)
    stuck = []
    
    for d in deals:
        stage = d.get("STAGE_ID", "")
        stage_info = STAGE_MAP.get(stage, {})
        # Проверяем только находящиеся в работе
        if stage_info.get("type") == "IN_WORK":
            created_str = d.get("DATE_CREATE", "")
            try:
                c_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_hours = (now - c_dt).total_seconds() / 3600
                if age_hours >= 24:
                    stuck.append({
                        "id": d["ID"],
                        "title": d.get("TITLE", "Сделка"),
                        "amount": float(d.get("OPPORTUNITY") or 0),
                        "stage_name": stage_info.get("name", stage),
                        "age_hours": int(age_hours)
                    })
            except:
                pass
    stuck.sort(key=lambda x: x["amount"], reverse=True)
    return stuck
