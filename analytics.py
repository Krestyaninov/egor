import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from config import STAGE_MAP
from b24_client import b24

# МСК таймзона (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    return datetime.now(MSK_TZ)

async def get_funnel_summary(start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    """Сбор и расчет точной сквозной воронки продаж для маркетинга"""
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00+03:00")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59+03:00")
    
    deals = await b24.get_deals_by_date(start_str, end_str)
    
    total_count = len(deals)
    total_amount = sum(float(d.get("OPPORTUNITY") or 0) for d in deals)
    
    # 1. Мусор / Спам / Дубли / Нецелевые
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

async def get_pipeline_stuck_summary(min_hours: int = 48) -> Dict[str, Any]:
    """Сбор и группировка зависших заказов в работе (без изменений более min_hours часов)"""
    now = get_now_msk()
    # За последние 30 дней для полного охвата активного пайплайна
    start_str = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00+03:00")
    
    deals = await b24.get_deals_by_date(start_str)
    
    total_in_work_count = 0
    total_in_work_amount = 0.0
    
    stuck_by_stage = {}
    total_stuck_count = 0
    total_stuck_amount = 0.0
    
    for d in deals:
        stage = d.get("STAGE_ID", "")
        stage_info = STAGE_MAP.get(stage, {})
        
        # Проверяем только находящиеся в работе
        if stage_info.get("type") == "IN_WORK":
            amt = float(d.get("OPPORTUNITY") or 0)
            total_in_work_count += 1
            total_in_work_amount += amt
            
            # Проверяем дату последнего изменения (DATE_MODIFY или DATE_CREATE)
            date_str = d.get("DATE_MODIFY") or d.get("DATE_CREATE") or ""
            try:
                mod_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                age_hours = (now - mod_dt).total_seconds() / 3600
                if age_hours >= min_hours:
                    stage_name = stage_info.get("name", stage)
                    if stage_name not in stuck_by_stage:
                        stuck_by_stage[stage_name] = {"count": 0, "amount": 0.0}
                    stuck_by_stage[stage_name]["count"] += 1
                    stuck_by_stage[stage_name]["amount"] += amt
                    total_stuck_count += 1
                    total_stuck_amount += amt
            except:
                pass
                
    breakdown = []
    for st_name, st_val in stuck_by_stage.items():
        pct = (st_val["count"] / total_stuck_count * 100) if total_stuck_count > 0 else 0.0
        breakdown.append({
            "stage_name": st_name,
            "count": st_val["count"],
            "amount": st_val["amount"],
            "pct": pct
        })
        
    breakdown.sort(key=lambda x: x["amount"], reverse=True)
    
    stuck_share_cnt = (total_stuck_count / total_in_work_count * 100) if total_in_work_count > 0 else 0.0
    stuck_share_amt = (total_stuck_amount / total_in_work_amount * 100) if total_in_work_amount > 0 else 0.0
    
    return {
        "min_hours": min_hours,
        "total_in_work_count": total_in_work_count,
        "total_in_work_amount": total_in_work_amount,
        "total_stuck_count": total_stuck_count,
        "total_stuck_amount": total_stuck_amount,
        "stuck_share_cnt": stuck_share_cnt,
        "stuck_share_amt": stuck_share_amt,
        "breakdown": breakdown
    }

async def get_7days_charts_and_stats() -> Tuple[io.BytesIO, Dict[str, Any]]:
    """Генерация графиков и данных за 7 полных закрытых дней (D-7 ... D-1)"""
    now = get_now_msk()
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_dt = yesterday - timedelta(days=6)
    end_dt = yesterday.replace(hour=23, minute=59, second=59)

    start_str = start_dt.strftime("%Y-%m-%dT00:00:00+03:00")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59+03:00")

    # 1. Заказы за 7 закрытых дней
    deals = await b24.get_deals_by_date(start_str, end_str)

    # 2. Выкупленные заказы за 7 дней (по CLOSEDATE)
    won_deals = await b24.get_won_deals_by_date(start_str, end_str)

    days = []
    day_labels = []
    daily_stats = {}

    ru_days = {'Mon': 'Пн', 'Tue': 'Вт', 'Wed': 'Ср', 'Thu': 'Чт', 'Fri': 'Пт', 'Sat': 'Сб', 'Sun': 'Вс'}

    for i in range(7):
        d = start_dt + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        lbl = d.strftime("%d.%m\n(%a)")
        for eng, ru in ru_days.items():
            lbl = lbl.replace(eng, ru)
        days.append(d_str)
        day_labels.append(lbl)
        daily_stats[d_str] = {
            "total_orders": 0,
            "qual_orders": 0,
            "won_revenue": 0.0,
            "won_count": 0
        }

    for d in deals:
        c_date = (d.get("DATE_CREATE") or "")[:10]
        if c_date in daily_stats:
            daily_stats[c_date]["total_orders"] += 1
            st_type = STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type")
            if st_type != "JUNK":
                daily_stats[c_date]["qual_orders"] += 1

    for d in won_deals:
        w_date = (d.get("CLOSEDATE") or d.get("DATE_MODIFY") or "")[:10]
        if w_date in daily_stats:
            amt = float(d.get("OPPORTUNITY") or 0)
            daily_stats[w_date]["won_revenue"] += amt
            daily_stats[w_date]["won_count"] += 1

    total_orders_list = [daily_stats[d]["total_orders"] for d in days]
    qual_rates_list = [
        (daily_stats[d]["qual_orders"] / daily_stats[d]["total_orders"] * 100) if daily_stats[d]["total_orders"] > 0 else 0.0
        for d in days
    ]
    won_rev_k_list = [daily_stats[d]["won_revenue"] / 1000 for d in days]
    won_counts_list = [daily_stats[d]["won_count"] for d in days]

    # Построение графиков
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9.5, 11), dpi=160)
    fig.patch.set_facecolor('#F8F9FA')

    c_blue = '#2563EB'
    c_purple = '#7C3AED'
    c_green = '#059669'
    c_red = '#DC2626'
    c_dark = '#0F172A'

    # 1. Заказы по дням
    ax1.set_facecolor('#FFFFFF')
    bars1 = ax1.bar(day_labels, total_orders_list, color=c_blue, width=0.52, edgecolor='#1D4ED8', linewidth=1.2, zorder=3)
    ax1.set_title('1. Входящий поток заказов (Динамика спроса)', fontsize=12, fontweight='bold', pad=10, color=c_dark)
    ax1.set_ylabel('Заказов (шт)', fontsize=10, fontweight='semibold', color=c_dark)
    ax1.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    max_orders = max(total_orders_list) if total_orders_list else 10
    ax1.set_ylim(0, max_orders * 1.25 + 2)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f"{int(yval)}", ha='center', va='bottom', fontsize=10, fontweight='bold', color=c_dark)

    # 2. Квалификация (%)
    ax2.set_facecolor('#FFFFFF')
    bars2 = ax2.bar(day_labels, qual_rates_list, color=c_purple, width=0.52, edgecolor='#6D28D9', linewidth=1.2, zorder=3)
    ax2.axhline(y=95, color=c_red, linestyle='--', linewidth=1.8, zorder=4, label='Цель: 95%')
    ax2.set_title('2. Доля квалифицированных заказов (% целевого трафика)', fontsize=12, fontweight='bold', pad=10, color=c_dark)
    ax2.set_ylabel('Квалификация (%)', fontsize=10, fontweight='semibold', color=c_dark)
    ax2.set_ylim(70, 105)
    ax2.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    ax2.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=9)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, yval + 0.8, f"{yval:.1f}%", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#4C1D95')

    # 3. Выручка WON
    ax3.set_facecolor('#FFFFFF')
    bars3 = ax3.bar(day_labels, won_rev_k_list, color=c_green, width=0.52, edgecolor='#047857', linewidth=1.2, zorder=3)
    ax3.set_title('3. Фактическая выручка выкупленных заказов (Оплаты за день)', fontsize=12, fontweight='bold', pad=10, color=c_dark)
    ax3.set_ylabel('Выручка (тыс. руб)', fontsize=10, fontweight='semibold', color=c_dark)
    ax3.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    max_rev = max(won_rev_k_list) if won_rev_k_list else 100
    ax3.set_ylim(0, max_rev * 1.25 + 20)
    for i, bar in enumerate(bars3):
        yval = bar.get_height()
        cnt = won_counts_list[i]
        lbl = f"{yval:,.0f}k\n({cnt} шт)" if yval > 0 else "0"
        ax3.text(bar.get_x() + bar.get_width()/2, yval + (max_rev * 0.02) + 1, lbl, ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#064E3B')

    plt.tight_layout(pad=2.0)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=160, facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    summary_stats = {
        "start_date": start_dt.strftime("%d.%m"),
        "end_date": end_dt.strftime("%d.%m.%Y"),
        "total_orders_7d": sum(total_orders_list),
        "avg_daily_orders": sum(total_orders_list) / 7,
        "avg_qual_rate": (sum([daily_stats[d]["qual_orders"] for d in days]) / sum(total_orders_list) * 100) if sum(total_orders_list) > 0 else 0.0,
        "total_won_revenue_7d": sum([daily_stats[d]["won_revenue"] for d in days]),
        "total_won_count_7d": sum(won_counts_list)
    }

    return buf, summary_stats

# =====================================================================
# НОВЫЙ БЛОК: Анализ нулевых сделок (без спама)
# =====================================================================

import numpy as np

async def get_zero_deals_data(mode: str = "7days") -> Dict[str, Any]:
    now = get_now_msk()
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if mode == "7days":
        start_dt = yesterday - timedelta(days=6)
        end_dt = yesterday
        title = "Динамика нулевых сделок (7 дней до вчера)"
        days = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        labels = [(start_dt + timedelta(days=i)).strftime("%d.%m") for i in range(7)]
        
        deals = await b24.get_deals_by_date(
            start_dt.strftime("%Y-%m-%dT00:00:00+03:00"),
            end_dt.strftime("%Y-%m-%dT23:59:59+03:00")
        )
        
        intervals_stat = {d: {"total": 0, "junk": 0, "qual": 0, "zero": 0} for d in days}
        for d in deals:
            d_str = (d.get("DATE_CREATE") or "")[:10]
            if d_str in intervals_stat:
                intervals_stat[d_str]["total"] += 1
                st_type = STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type")
                if st_type == "JUNK":
                    intervals_stat[d_str]["junk"] += 1
                else:
                    intervals_stat[d_str]["qual"] += 1
                    opp = float(d.get("OPPORTUNITY") or 0)
                    if opp == 0:
                        intervals_stat[d_str]["zero"] += 1
                        
        items = []
        for d, lbl in zip(days, labels):
            s = intervals_stat[d]
            rate = (s["zero"] / s["qual"] * 100) if s["qual"] > 0 else 0.0
            items.append({
                "key": d,
                "label": lbl,
                "total": s["total"],
                "qual": s["qual"],
                "junk": s["junk"],
                "zero": s["zero"],
                "rate": rate
            })
    else: # 5weeks
        end_dt = yesterday
        mon_this_week = yesterday - timedelta(days=yesterday.weekday())
        start_dt = mon_this_week - timedelta(weeks=4)
        title = "Динамика нулевых сделок (5 недель до вчера)"
        
        deals = await b24.get_deals_by_date(
            start_dt.strftime("%Y-%m-%dT00:00:00+03:00"),
            end_dt.strftime("%Y-%m-%dT23:59:59+03:00")
        )
        
        weeks = []
        for w in range(5):
            w_start = start_dt + timedelta(weeks=w)
            w_end = min(w_start + timedelta(days=6), end_dt)
            w_label = f"{w_start.strftime('%d.%m')}–{w_end.strftime('%d.%m')}"
            weeks.append({
                "start": w_start,
                "end": w_end,
                "label": w_label,
                "total": 0,
                "junk": 0,
                "qual": 0,
                "zero": 0
            })
            
        for d in deals:
            try:
                dt = datetime.fromisoformat(d["DATE_CREATE"].replace("Z", "+00:00"))
                for wb in weeks:
                    w_start_msk = wb["start"].replace(tzinfo=MSK_TZ, hour=0, minute=0, second=0)
                    w_end_msk = wb["end"].replace(tzinfo=MSK_TZ, hour=23, minute=59, second=59)
                    if w_start_msk <= dt <= w_end_msk:
                        wb["total"] += 1
                        st_type = STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type")
                        if st_type == "JUNK":
                            wb["junk"] += 1
                        else:
                            wb["qual"] += 1
                            opp = float(d.get("OPPORTUNITY") or 0)
                            if opp == 0:
                                wb["zero"] += 1
                        break
            except:
                pass
                
        items = []
        for wb in weeks:
            rate = (wb["zero"] / wb["qual"] * 100) if wb["qual"] > 0 else 0.0
            items.append({
                "label": wb["label"],
                "total": wb["total"],
                "qual": wb["qual"],
                "junk": wb["junk"],
                "zero": wb["zero"],
                "rate": rate
            })
            
    total_qual = sum(x["qual"] for x in items)
    total_zero = sum(x["zero"] for x in items)
    total_junk = sum(x.get("junk", 0) for x in items)
    overall_rate = (total_zero / total_qual * 100) if total_qual > 0 else 0.0
    
    return {
        "mode": mode,
        "title": title,
        "start_date": start_dt.strftime("%d.%m.%Y"),
        "end_date": end_dt.strftime("%d.%m.%Y"),
        "items": items,
        "total_qual": total_qual,
        "total_zero": total_zero,
        "total_junk": total_junk,
        "overall_rate": overall_rate
    }

def generate_zero_deals_chart(data: Dict[str, Any]) -> io.BytesIO:
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax1 = plt.subplots(figsize=(9.5, 5.2), dpi=160)
    fig.patch.set_facecolor('#F8F9FA')
    ax1.set_facecolor('#FFFFFF')

    labels = [x["label"] for x in data["items"]]
    zero_counts = [x["zero"] for x in data["items"]]
    rates = [x["rate"] for x in data["items"]]
    
    x = np.arange(len(labels))
    width = 0.45

    # Левая ось: количество нулевых сделок (шт)
    c_bar = '#3B82F6'
    c_edge = '#1D4ED8'
    bars = ax1.bar(x, zero_counts, width=width, color=c_bar, edgecolor=c_edge, linewidth=1.2, zorder=3, label="Нулевые сделки (шт)")
    ax1.set_ylabel("Количество нулевых сделок (шт)", fontsize=10, fontweight="bold", color="#1E3A8A")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=10, fontweight="bold")
    ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    
    max_count = max(zero_counts) if zero_counts else 10
    ax1.set_ylim(0, max_count * 1.35 + 2)

    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h + (max_count * 0.02) + 0.3, f"{int(h)} шт", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color="#1E3A8A")

    # Правая ось: доля от квалифицированных (%)
    ax2 = ax1.twinx()
    c_line = '#DC2626'
    line = ax2.plot(x, rates, color=c_line, marker='o', linewidth=2.5, markersize=7, zorder=5, label="% от квал. сделок")
    ax2.set_ylabel("Доля от квал. сделок (%)", fontsize=10, fontweight="bold", color=c_line)
    
    max_rate = max(rates) if rates else 50
    ax2.set_ylim(0, max(max_rate * 1.3, 20))
    ax2.grid(False)

    for i, r in enumerate(rates):
        ax2.text(x[i], r + (max_rate * 0.03) + 1.0, f"{r:.1f}%", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#991B1B')

    title_text = f"{data['title']}\nИтого: {data['total_zero']} из {data['total_qual']} квал. сделок ({data['overall_rate']:.1f}%)"
    ax1.set_title(title_text, fontsize=11.5, fontweight='bold', pad=12, color='#0F172A')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=9)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=160, facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf

# =====================================================================
# НОВЫЙ БЛОК: Анализ продаж по товарным группам (Apple vs Другие)
# =====================================================================

PRODUCT_CATEGORIES = ["Смартфоны", "Планшеты", "Ноутбуки", "Смарт-часы", "Наушники", "Другие товары"]
_PRODUCT_META_CACHE: Dict[int, Dict[str, Any]] = {}

def map_product_category(type_prefix: str, product_name: str) -> str:
    tp = (type_prefix or "").strip().lower()
    nm = (product_name or "").lower()
    if "смартфон" in tp or "смартфон" in nm:
        return "Смартфоны"
    elif "планшет" in tp or "ipad" in nm:
        return "Планшеты"
    elif "ноутбук" in tp or "macbook" in nm or "ноутбук" in nm:
        return "Ноутбуки"
    elif "смарт-час" in tp or "часы" in tp or "apple watch" in nm:
        return "Смарт-часы"
    elif "наушник" in tp or "гарнитур" in tp or "airpods" in nm or "наушники" in nm:
        return "Наушники"
    return "Другие товары"

def is_apple_product(meta: Dict[str, Any]) -> bool:
    p75 = meta.get("p75")
    p75_val = p75.get("value") if isinstance(p75, dict) else p75
    if str(p75_val) == "2150":
        return True
    nm = (meta.get("name") or "").lower()
    return any(k in nm for k in ["apple", "iphone", "ipad", "macbook", "airpods", "apple watch", "imac", "mac mini", "mac studio"])

async def get_products_meta_batch(product_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    missing = [pid for pid in product_ids if pid not in _PRODUCT_META_CACHE and pid > 0]
    chunk_size = 50
    for i in range(0, len(missing), chunk_size):
        chunk = missing[i:i+chunk_size]
        cmd = {f"p_{pid}": f"crm.product.get?id={pid}" for pid in chunk}
        batch_res = await b24.call("batch", {"cmd": cmd})
        res_data = batch_res.get("result", {}).get("result", {})
        for pid_key, p_res in res_data.items():
            try:
                pid = int(pid_key.replace("p_", ""))
                ptg = p_res.get("PROPERTY_60570")
                tp = p_res.get("PROPERTY_60389")
                p75 = p_res.get("PROPERTY_75")
                ptg_val = ptg.get("value") if isinstance(ptg, dict) else ptg
                tp_val = tp.get("value") if isinstance(tp, dict) else tp
                _PRODUCT_META_CACHE[pid] = {
                    "name": p_res.get("NAME") or "",
                    "group": ptg_val or "",
                    "type": tp_val or "",
                    "p75": p75
                }
            except Exception:
                pass
    return _PRODUCT_META_CACHE

async def get_deals_productrows_batch(deal_ids: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    deal_products: Dict[str, List[Dict[str, Any]]] = {}
    chunk_size = 50
    for i in range(0, len(deal_ids), chunk_size):
        chunk = deal_ids[i:i+chunk_size]
        cmd = {f"d_{did}": f"crm.deal.productrows.get?id={did}" for did in chunk}
        batch_res = await b24.call("batch", {"cmd": cmd})
        res_data = batch_res.get("result", {}).get("result", {})
        for did_key, rows in res_data.items():
            did = did_key.replace("d_", "")
            deal_products[did] = rows or []
    return deal_products

def get_period_dates(period: str) -> Tuple[datetime, datetime, str]:
    now = get_now_msk()
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == "yesterday":
        start_dt = yesterday
        end_dt = yesterday
        title = f"Вчера ({yesterday.strftime('%d.%m.%Y')})"
    elif period == "this_week":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
        if start_dt > yesterday:
            start_dt = yesterday
        end_dt = yesterday
        title = f"Текущая неделя ({start_dt.strftime('%d.%m')} – {yesterday.strftime('%d.%m.%Y')})"
    elif period == "prev_week":
        mon_this_week = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
        start_dt = mon_this_week - timedelta(days=7)
        end_dt = mon_this_week - timedelta(days=1)
        title = f"Прошлая неделя ({start_dt.strftime('%d.%m')} – {end_dt.strftime('%d.%m.%Y')})"
    elif period == "this_month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_dt > yesterday:
            start_dt = yesterday
        end_dt = yesterday
        title = f"Текущий месяц ({start_dt.strftime('%d.%m')} – {yesterday.strftime('%d.%m.%Y')})"
    elif period == "prev_month":
        first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = first_this_month - timedelta(days=1)
        start_dt = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        title = f"Прошлый месяц ({start_dt.strftime('%d.%m')} – {end_dt.strftime('%d.%m.%Y')})"
    else:
        start_dt = yesterday
        end_dt = yesterday
        title = f"Вчера ({yesterday.strftime('%d.%m.%Y')})"
        
    return start_dt, end_dt, title

async def get_product_types_data(period: str = "yesterday") -> Dict[str, Any]:
    start_dt, end_dt, title = get_period_dates(period)
    
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00+03:00")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59+03:00")
    
    deals = await b24.get_deals_by_date(start_str, end_str)
    
    # Исключаем спам/дубли/нецелевые
    qual_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") != "JUNK"]
    deal_ids = [int(d["ID"]) for d in qual_deals]
    
    deal_products = await get_deals_productrows_batch(deal_ids)
    
    # Собираем уникальные ID продуктов
    all_pids = set()
    for rows in deal_products.values():
        for r in rows:
            pid = r.get("PRODUCT_ID")
            if pid and int(pid) > 0:
                all_pids.add(int(pid))
                
    prod_meta = await get_products_meta_batch(list(all_pids))
    
    # Инициализируем структуру статистики
    stats = {}
    for cat in PRODUCT_CATEGORIES:
        stats[cat] = {
            "Apple": {"deals": 0, "won": 0, "amount": 0.0, "cr": 0.0, "avg_check": 0.0},
            "Другие": {"deals": 0, "won": 0, "amount": 0.0, "cr": 0.0, "avg_check": 0.0}
        }
        
    target_deals_count = 0
    
    for d in qual_deals:
        did = str(d["ID"])
        rows = deal_products.get(did, [])
        is_won = (STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "WON")
        
        deal_cat_amounts = {}
        has_target = False
        
        for r in rows:
            pid = r.get("PRODUCT_ID")
            if not pid or int(pid) not in prod_meta:
                continue
            meta = prod_meta[int(pid)]
            if meta["group"] not in ["Товары", "Комплектующие"]:
                continue
            has_target = True
            cat = map_product_category(meta["type"], meta["name"])
            brand = "Apple" if is_apple_product(meta) else "Другие"
            price = float(r.get("PRICE") or 0) * float(r.get("QUANTITY") or 1)
            key = (cat, brand)
            deal_cat_amounts[key] = deal_cat_amounts.get(key, 0.0) + price
            
        if has_target:
            target_deals_count += 1
            
        for (cat, brand), amt in deal_cat_amounts.items():
            sub = stats[cat][brand]
            sub["deals"] += 1
            if is_won:
                sub["won"] += 1
            sub["amount"] += amt
            
    # Вычисляем производные метрики (CR и средний чек)
    for cat in PRODUCT_CATEGORIES:
        for brand in ["Apple", "Другие"]:
            s = stats[cat][brand]
            s["cr"] = (s["won"] / s["deals"] * 100) if s["deals"] > 0 else 0.0
            s["avg_check"] = (s["amount"] / s["deals"]) if s["deals"] > 0 else 0.0
            
    return {
        "period": period,
        "title": title,
        "start_date": start_dt.strftime("%d.%m.%Y"),
        "end_date": end_dt.strftime("%d.%m.%Y"),
        "total_deals": len(qual_deals),
        "total_target_deals": target_deals_count,
        "stats": stats
    }

def generate_product_types_chart(data: Dict[str, Any]) -> io.BytesIO:
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 11), dpi=160)
    fig.patch.set_facecolor('#F8F9FA')

    stats = data["stats"]
    title = data["title"]

    c_apple = '#2563EB'
    c_other = '#F59E0B'
    c_dark = '#0F172A'

    x = np.arange(len(PRODUCT_CATEGORIES))
    width = 0.36

    apple_deals = [stats[c]["Apple"]["deals"] for c in PRODUCT_CATEGORIES]
    other_deals = [stats[c]["Другие"]["deals"] for c in PRODUCT_CATEGORIES]

    apple_cr = [stats[c]["Apple"]["cr"] for c in PRODUCT_CATEGORIES]
    other_cr = [stats[c]["Другие"]["cr"] for c in PRODUCT_CATEGORIES]

    apple_chk = [stats[c]["Apple"]["avg_check"] / 1000 for c in PRODUCT_CATEGORIES]
    other_chk = [stats[c]["Другие"]["avg_check"] / 1000 for c in PRODUCT_CATEGORIES]

    # 1. Лиды
    ax1.set_facecolor('#FFFFFF')
    b1 = ax1.bar(x - width/2, apple_deals, width, label='Apple', color=c_apple, edgecolor='#1D4ED8', zorder=3)
    b2 = ax1.bar(x + width/2, other_deals, width, label='Другие бренды', color=c_other, edgecolor='#D97706', zorder=3)
    ax1.set_title(f'1. Количество входящих лидов (сделок) | {title}', fontsize=11, fontweight='bold', pad=8, color=c_dark)
    ax1.set_ylabel('Сделок (шт)', fontsize=9, fontweight='bold', color=c_dark)
    ax1.set_xticks(x)
    ax1.set_xticklabels(PRODUCT_CATEGORIES, fontsize=9.5, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    max_d = max(max(apple_deals or [0]), max(other_deals or [0]), 5)
    ax1.set_ylim(0, max_d * 1.35 + 1)
    ax1.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=9)
    for bar in b1:
        h = bar.get_height()
        if h > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, h + 0.3, f"{int(h)}", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1E3A8A')
    for bar in b2:
        h = bar.get_height()
        if h > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, h + 0.3, f"{int(h)}", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#92400E')

    # 2. Конверсия выкупа (%)
    ax2.set_facecolor('#FFFFFF')
    b3 = ax2.bar(x - width/2, apple_cr, width, label='Apple', color='#3B82F6', edgecolor='#1D4ED8', zorder=3)
    b4 = ax2.bar(x + width/2, other_cr, width, label='Другие бренды', color='#FBBF24', edgecolor='#D97706', zorder=3)
    ax2.set_title('2. Процент выкупа (CR в статус WON от квал. сделок)', fontsize=11, fontweight='bold', pad=8, color=c_dark)
    ax2.set_ylabel('Выкуп (%)', fontsize=9, fontweight='bold', color=c_dark)
    ax2.set_xticks(x)
    ax2.set_xticklabels(PRODUCT_CATEGORIES, fontsize=9.5, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    ax2.set_ylim(0, 115)
    for bar in b3:
        h = bar.get_height()
        if h > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, h + 1.5, f"{h:.0f}%", ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#1E3A8A')
    for bar in b4:
        h = bar.get_height()
        if h > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, h + 1.5, f"{h:.0f}%", ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#92400E')

    # 3. Средний чек (тыс. руб)
    ax3.set_facecolor('#FFFFFF')
    b5 = ax3.bar(x - width/2, apple_chk, width, label='Apple', color='#10B981', edgecolor='#047857', zorder=3)
    b6 = ax3.bar(x + width/2, other_chk, width, label='Другие бренды', color='#6EE7B7', edgecolor='#059669', zorder=3)
    ax3.set_title('3. Средний чек товарной позиции (тыс. руб)', fontsize=11, fontweight='bold', pad=8, color=c_dark)
    ax3.set_ylabel('Ср. чек (тыс. руб)', fontsize=9, fontweight='bold', color=c_dark)
    ax3.set_xticks(x)
    ax3.set_xticklabels(PRODUCT_CATEGORIES, fontsize=9.5, fontweight='bold')
    ax3.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    max_c = max(max(apple_chk or [0]), max(other_chk or [0]), 20)
    ax3.set_ylim(0, max_c * 1.35 + 5)
    for bar in b5:
        h = bar.get_height()
        if h > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, h + (max_c * 0.02) + 0.5, f"{h:,.0f}k", ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#065F46')
    for bar in b6:
        h = bar.get_height()
        if h > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, h + (max_c * 0.02) + 0.5, f"{h:,.0f}k", ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#065F46')

    plt.tight_layout(pad=2.0)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=160, facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf

