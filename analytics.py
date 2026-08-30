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
