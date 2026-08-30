import io
import asyncio
from datetime import datetime, timedelta, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from b24_client import b24
from config import STAGE_MAP

MSK_TZ = timezone(timedelta(hours=3))

def get_now_msk() -> datetime:
    return datetime.now(MSK_TZ)

async def get_chart_data():
    now = get_now_msk()
    # 7 полных закрытых дней: с yesterday - 6 days до yesterday
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_dt = yesterday - timedelta(days=6)
    end_dt = yesterday.replace(hour=23, minute=59, second=59)

    start_str = start_dt.strftime("%Y-%m-%dT00:00:00+03:00")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59+03:00")

    # 1. Все созданные сделки за 7 дней
    deals = await b24.get_deals_by_date(start_str, end_str)

    # 2. Все сделки, выведенные в WON за эти 7 дней (по CLOSEDATE)
    won_deals_raw = await b24.call("crm.deal.list", {
        "filter": {
            "STAGE_ID": "WON",
            ">=CLOSEDATE": start_str,
            "<=CLOSEDATE": end_str
        },
        "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSEDATE"]
    })
    won_deals = won_deals_raw.get("result", [])

    # Инициализация дней
    days = []
    day_labels = []
    daily_stats = {}

    for i in range(7):
        d = start_dt + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        lbl = d.strftime("%d.%m\n(%a)")
        # русские дни недели
        ru_days = {'Mon': 'Пн', 'Tue': 'Вт', 'Wed': 'Ср', 'Thu': 'Чт', 'Fri': 'Пт', 'Sat': 'Сб', 'Sun': 'Вс'}
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

    # Подсчет входящих и квалифицированных
    for d in deals:
        c_date = (d.get("DATE_CREATE") or "")[:10]
        if c_date in daily_stats:
            daily_stats[c_date]["total_orders"] += 1
            st_type = STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type")
            if st_type != "JUNK":
                daily_stats[c_date]["qual_orders"] += 1

    # Подсчет фактической выручки WON
    for d in won_deals:
        w_date = (d.get("CLOSEDATE") or d.get("DATE_MODIFY") or "")[:10]
        if w_date in daily_stats:
            amt = float(d.get("OPPORTUNITY") or 0)
            daily_stats[w_date]["won_revenue"] += amt
            daily_stats[w_date]["won_count"] += 1

    return days, day_labels, daily_stats

def generate_analytics_chart(days, day_labels, daily_stats) -> io.BytesIO:
    # Данные для графиков
    total_orders = [daily_stats[d]["total_orders"] for d in days]
    qual_rates = [
        (daily_stats[d]["qual_orders"] / daily_stats[d]["total_orders"] * 100) if daily_stats[d]["total_orders"] > 0 else 0
        for d in days
    ]
    won_revenues = [daily_stats[d]["won_revenue"] / 1000 for d in days] # в тыс. руб
    won_counts = [daily_stats[d]["won_count"] for d in days]

    # Стилизация графиков
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), dpi=150)
    fig.patch.set_facecolor('#F8F9FA')

    # Цветовая палитра
    c_blue = '#2563EB'
    c_green = '#10B981'
    c_red = '#EF4444'
    c_dark = '#1E293B'

    # --- График 1: Количество заказов по дням ---
    ax1.set_facecolor('#FFFFFF')
    bars1 = ax1.bar(day_labels, total_orders, color=c_blue, width=0.55, edgecolor='#1D4ED8', linewidth=1.2, zorder=3)
    ax1.set_title('1. Входящий поток заказов (Динамика спроса)', fontsize=13, fontweight='bold', pad=12, color=c_dark)
    ax1.set_ylabel('Заказов (шт)', fontsize=11, fontweight='semibold', color=c_dark)
    ax1.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    max_orders = max(total_orders) if total_orders else 10
    ax1.set_ylim(0, max_orders * 1.25 + 2)

    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f"{int(yval)}", ha='center', va='bottom', fontsize=11, fontweight='bold', color=c_dark)

    # --- График 2: Уровень квалификации заказов (%) ---
    ax2.set_facecolor('#FFFFFF')
    bars2 = ax2.bar(day_labels, qual_rates, color='#8B5CF6', width=0.55, edgecolor='#6D28D9', linewidth=1.2, zorder=3)
    ax2.axhline(y=95, color=c_red, linestyle='--', linewidth=2, zorder=4, label='Целевой уровень (95%)')
    ax2.set_title('2. Доля квалифицированных заказов (% целевого трафика)', fontsize=13, fontweight='bold', pad=12, color=c_dark)
    ax2.set_ylabel('Квалификация (%)', fontsize=11, fontweight='semibold', color=c_dark)
    ax2.set_ylim(70, 105)
    ax2.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    ax2.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=10)

    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, yval + 0.8, f"{yval:.1f}%", ha='center', va='bottom', fontsize=10, fontweight='bold', color='#4C1D95')

    # --- График 3: Фактическая кассовая выручка WON ---
    ax3.set_facecolor('#FFFFFF')
    bars3 = ax3.bar(day_labels, won_revenues, color=c_green, width=0.55, edgecolor='#047857', linewidth=1.2, zorder=3)
    ax3.set_title('3. Фактическая выручка выкупленных заказов (Оплаты за день)', fontsize=13, fontweight='bold', pad=12, color=c_dark)
    ax3.set_ylabel('Выручка (тыс. ₽)', fontsize=11, fontweight='semibold', color=c_dark)
    ax3.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    max_rev = max(won_revenues) if won_revenues else 100
    ax3.set_ylim(0, max_rev * 1.25 + 20)

    for i, bar in enumerate(bars3):
        yval = bar.get_height()
        cnt = won_counts[i]
        ax3.text(bar.get_x() + bar.get_width()/2, yval + (max_rev * 0.02), f"{yval:,.0f}k ₽\n({cnt} шт)", ha='center', va='bottom', fontsize=10, fontweight='bold', color='#064E3B')

    plt.tight_layout(pad=2.5)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf

async def main():
    print("Собираем данные для графиков...")
    days, day_labels, daily_stats = await get_chart_data()
    print("Дни:", days)
    for d, st in daily_stats.items():
        print(f"  {d}: Заказов={st['total_orders']}, Квал={st['qual_orders']}, Выручка WON={st['won_revenue']:,.0f} ₽ ({st['won_count']} шт)")
    
    buf = generate_analytics_chart(days, day_labels, daily_stats)
    with open("test_chart.png", "wb") as f:
        f.write(buf.read())
    print("График успешно сгенерирован в test_chart.png!")

if __name__ == "__main__":
    asyncio.run(main())
