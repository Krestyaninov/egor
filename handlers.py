import logging
import html
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from datetime import timedelta
from analytics import get_now_msk, get_funnel_summary, get_categories_breakdown, get_pipeline_stuck_deals

logger = logging.getLogger(__name__)
router = Router()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📊 Сегодня (Пульс)"), KeyboardButton(text="🌅 Вчера (Итоги)")],
        [KeyboardButton(text="📱 Категории & Маржа"), KeyboardButton(text="🛑 Причины отказов")],
        [KeyboardButton(text="⏳ Зависшие сделки (Pipeline)"), KeyboardButton(text="🗓 Последние 7 дней")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 <b>Привет! Я Аналитик Егор (@egor_quapmi_bot)</b> — твой AI-ассистент по CRM-аналитике и контролю воронки продаж.\n\n"
        "🎯 <b>Что я умею:</b>\n"
        "• 📊 <b>Сквозная воронка:</b> Входящие, квалификация, выкуп и отказы\n"
        "• 💰 <b>Маржа и прибыль:</b> Расчет чистой прибыли по выкупленным категориям\n"
        "• 🛑 <b>Причины отказов:</b> Расшифровка с реальными названиями и суммами потерь\n"
        "• ⏳ <b>Pipeline:</b> Контроль заказов в работе и задержек > 24ч\n\n"
        "👇 Выбирай нужный срез в меню ниже:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.message(F.text == "📊 Сегодня (Пульс)")
@router.message(Command("today"))
async def handle_today(message: Message):
    wait_msg = await message.answer("⏳ Собираю свежие данные из CRM за сегодня...")
    now = get_now_msk()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    data = await get_funnel_summary(today_start, now)
    
    text = (
        f"📊 <b>Пульс CRM | Сегодня ({now.strftime('%d.%m.%Y')})</b>\n\n"
        f"📥 <b>Входящий поток:</b>\n"
        f"• Всего заказов: <b>{data['total_count']} шт.</b> на <b>{data['total_amount']:,.0f} ₽</b>\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> ({data['qual_rate']:.1f}%) на <b>{data['qual_amount']:,.0f} ₽</b>\n"
        f"• Нецелевой / спам / дубли: <b>{data['junk_count']} шт.</b>\n\n"
        f"📈 <b>Результаты воронки:</b>\n"
        f"├── 🟢 <b>Выкуплено (WON):</b> <b>{data['won_count']} шт.</b> на <b>{data['won_amount']:,.0f} ₽</b>\n"
        f"│   └ <i>Конверсия в выкуп (от квал.):</i> <b>{data['cr_qual']:.1f}%</b>\n"
        f"├── 🟡 <b>В работе / доставке:</b> <b>{data['in_work_count']} шт.</b> на <b>{data['in_work_amount']:,.0f} ₽</b>\n"
        f"└── 🔴 <b>Отказы:</b> <b>{data['lose_count']} шт.</b> на <b>{data['lose_amount']:,.0f} ₽</b>\n"
    )
    
    if data['in_work_breakdown']:
        text += "\n📦 <b>Где сейчас заказы в работе:</b>\n"
        for st_name, st_val in data['in_work_breakdown'][:4]:
            text += f"• {html.escape(st_name)}: <b>{st_val['count']} шт.</b> ({st_val['amount']:,.0f} ₽)\n"
            
    if data['reasons']:
        text += "\n🛑 <b>Отказы дня:</b>\n"
        for r_name, r_val in data['reasons'][:2]:
            text += f"• {html.escape(r_name)}: <b>{r_val['count']} шт.</b> ({r_val['amount']:,.0f} ₽)\n"
            
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "🌅 Вчера (Итоги)")
@router.message(Command("yesterday"))
async def handle_yesterday(message: Message):
    wait_msg = await message.answer("⏳ Формирую отчет за вчерашний день...")
    now = get_now_msk()
    yesterday = now - timedelta(days=1)
    
    data = await get_funnel_summary(yesterday, yesterday)
    categories = await get_categories_breakdown(data["won_deals"])
    
    total_profit = sum(c["profit"] for c in categories)
    margin_pct = (total_profit / data['won_amount'] * 100) if data['won_amount'] > 0 else 0
    
    text = (
        f"🌅 <b>Итоги CRM | Вчера ({yesterday.strftime('%d.%m.%Y')})</b>\n\n"
        f"📥 <b>Воронка:</b>\n"
        f"• Создано: <b>{data['total_count']} шт.</b> ({data['total_amount']:,.0f} ₽)\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> ({data['qual_rate']:.1f}%)\n"
        f"• Выкуплено: <b>{data['won_count']} шт.</b> на <b>{data['won_amount']:,.0f} ₽</b>\n"
        f"• Конверсия (CR Qual): <b>{data['cr_qual']:.1f}%</b>\n"
        f"• Заказов осталось в работе: <b>{data['in_work_count']} шт.</b> ({data['in_work_amount']:,.0f} ₽)\n"
        f"• Отказы: <b>{data['lose_count']} шт.</b> ({data['lose_amount']:,.0f} ₽)\n\n"
        f"💰 <b>Финансы и маржа:</b>\n"
        f"• Расчетная чистая прибыль: <b>+{total_profit:,.0f} ₽</b> (Маржа: <b>{margin_pct:.1f}%</b>)\n\n"
        f"🏆 <b>Топ категорий по выкупу:</b>\n"
    )
    
    for c in categories[:4]:
        c_name = html.escape(str(c['category']))
        text += f"• <b>{c_name}</b>: {c['count']} шт. | Выручка: {c['revenue']:,.0f} ₽ | ЧП: <b>+{c['profit']:,.0f} ₽</b> ({c['margin_pct']:.1f}%)\n"
        
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "📱 Категории & Маржа")
@router.message(Command("categories"))
async def handle_categories(message: Message):
    wait_msg = await message.answer("⏳ Анализирую маржинальность по выкупленным категориям за 7 дней...")
    now = get_now_msk()
    week_ago = now - timedelta(days=7)
    
    data = await get_funnel_summary(week_ago, now)
    categories = await get_categories_breakdown(data["won_deals"])
    
    total_rev = sum(c["revenue"] for c in categories)
    total_profit = sum(c["profit"] for c in categories)
    
    text = (
        f"📱 <b>Маржинальность выкупленных заказов (За 7 дней)</b>\n"
        f"Выручка: <b>{total_rev:,.0f} ₽</b> | Расчетная прибыль: <b>{total_profit:,.0f} ₽</b>\n\n"
    )
    
    for c in categories:
        emoji = "🟢" if c["margin_pct"] >= 10.0 else ("🟡" if c["margin_pct"] >= 6.0 else "🔴")
        c_name = html.escape(str(c['category']))
        text += f"{emoji} <b>{c_name}</b>\n   {c['count']} шт. | Выручка: {c['revenue']:,.0f} ₽ | ЧП: <b>+{c['profit']:,.0f} ₽</b> (Маржа: {c['margin_pct']:.1f}%)\n"
        
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "🛑 Причины отказов")
@router.message(Command("reasons"))
async def handle_reasons(message: Message):
    wait_msg = await message.answer("⏳ Собираю структуру отказов за последние 7 дней...")
    now = get_now_msk()
    week_ago = now - timedelta(days=7)
    
    data = await get_funnel_summary(week_ago, now)
    
    text = (
        f"🛑 <b>Анализ причин отказов в CRM (За 7 дней)</b>\n"
        f"Всего отказов: <b>{data['lose_count']} шт.</b> на сумму <b>{data['lose_amount']:,.0f} ₽</b>\n\n"
        f"📉 <b>Структура потерь выручки:</b>\n"
    )
    
    if not data["reasons"]:
        text += "<i>Отказов за указанный период не зафиксировано.</i>"
    else:
        for reason, stat in data["reasons"]:
            share = (stat["amount"] / data["lose_amount"] * 100) if data["lose_amount"] > 0 else 0
            r_name = html.escape(str(reason))
            text += f"• <b>{r_name}</b>\n   {stat['count']} сделок | <b>{stat['amount']:,.0f} ₽</b> ({share:.1f}% от потерь)\n"
        
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "⏳ Зависшие сделки (Pipeline)")
@router.message(Command("pipeline"))
async def handle_pipeline(message: Message):
    wait_msg = await message.answer("⏳ Сканирую зависшие сделки в воронке...")
    stuck = await get_pipeline_stuck_deals()
    
    if not stuck:
        await wait_msg.edit_text("🎉 Отлично! В воронке нет зависших сделок старше 24 часов.")
        return
        
    total_stuck_amt = sum(s["amount"] for s in stuck)
    text = (
        f"⏳ <b>Зависшие заказы в работе (> 24ч без движения)</b>\n"
        f"Всего зависло: <b>{len(stuck)} сделок</b> на сумму <b>{total_stuck_amt:,.0f} ₽</b>\n\n"
        f"⚠️ <b>Топ сделок, требующих ускорения менеджерами:</b>\n"
    )
    
    for s in stuck[:6]:
        title = html.escape(str(s['title'][:25]))
        stage = html.escape(str(s['stage_name']))
        text += f"• <b>[ID {s['id']}]</b> {title}...\n   Сумма: <b>{s['amount']:,.0f} ₽</b> | {stage} (висит {s['age_hours']} ч.)\n"
        
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "🗓 Последние 7 дней")
@router.message(Command("week"))
async def handle_week(message: Message):
    wait_msg = await message.answer("⏳ Считаю недельную динамику...")
    now = get_now_msk()
    week_ago = now - timedelta(days=7)
    
    data = await get_funnel_summary(week_ago, now)
    categories = await get_categories_breakdown(data["won_deals"])
    total_profit = sum(c["profit"] for c in categories)
    margin_pct = (total_profit / data['won_amount'] * 100) if data['won_amount'] > 0 else 0
    
    text = (
        f"🗓 <b>Недельный отчет CRM ({week_ago.strftime('%d.%m')} - {now.strftime('%d.%m.%Y')})</b>\n\n"
        f"📥 <b>Воронка:</b>\n"
        f"• Всего заказов: <b>{data['total_count']} шт.</b> ({data['total_amount']:,.0f} ₽)\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> ({data['qual_rate']:.1f}%)\n"
        f"• Нецелевые / спам / дубли: <b>{data['junk_count']} шт.</b>\n"
        f"• Выкуплено (WON): <b>{data['won_count']} шт.</b> ({data['won_amount']:,.0f} ₽)\n"
        f"• <b>Конверсия в выкуп (CR Qual):</b> <b>{data['cr_qual']:.1f}%</b>\n"
        f"• Заказов в работе сейчас: <b>{data['in_work_count']} шт.</b> ({data['in_work_amount']:,.0f} ₽)\n"
        f"• Отказы: <b>{data['lose_count']} шт.</b> (Потери: <b>{data['lose_amount']:,.0f} ₽</b>)\n\n"
        f"💰 <b>Финансы:</b>\n"
        f"• Расчетная чистая прибыль: <b>+{total_profit:,.0f} ₽</b> (Маржа: <b>{margin_pct:.1f}%</b>)\n\n"
        f"💡 Используйте меню для детального среза по категориям и причинам отказов!"
    )
    await wait_msg.edit_text(text, parse_mode="HTML")
