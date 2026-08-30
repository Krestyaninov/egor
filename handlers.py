import logging
import html
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from datetime import timedelta
from analytics import (
    get_now_msk,
    get_funnel_summary,
    get_pipeline_stuck_summary,
    get_7days_charts_and_stats
)

logger = logging.getLogger(__name__)
router = Router()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📊 Сегодня (Пульс)"), KeyboardButton(text="🌅 Вчера (Итоги)")],
        [KeyboardButton(text="📈 Графики & Динамика"), KeyboardButton(text="🗓 Недельный отчет (7 дней)")],
        [KeyboardButton(text="⏳ Зависшие сделки (>48ч)"), KeyboardButton(text="🛑 Причины отказов")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "👋 <b>Привет! Я Аналитик Егор (@egor_quapmi_bot)</b> — твой AI-ассистент по CRM-аналитике и контролю воронки продаж.\n\n"
        "🎯 <b>Доступные отчеты:</b>\n"
        "• 📊 <b>Сегодня (Пульс):</b> Входящий поток, квалификация, выкуп и отказы день-в-день\n"
        "• 🌅 <b>Вчера (Итоги):</b> Итоги прошедшего дня и конверсия в выкуп\n"
        "• 📈 <b>Графики & Динамика:</b> 3 диаграммы по спросу, качеству трафика (цель 95%) и выручке WON\n"
        "• 🗓 <b>Недельный отчет:</b> Сводка за полные 7 закрытых дней\n"
        "• ⏳ <b>Зависшие сделки (>48ч):</b> Структура заказов без движения по статусам и суммам\n"
        "• 🛑 <b>Причины отказов:</b> Рейтинг потерь выручки с понятными причинами\n\n"
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
    
    text = (
        f"🌅 <b>Итоги CRM | Вчера ({yesterday.strftime('%d.%m.%Y')})</b>\n\n"
        f"📥 <b>Воронка продаж:</b>\n"
        f"• Всего заказов: <b>{data['total_count']} шт.</b> на <b>{data['total_amount']:,.0f} ₽</b>\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> (<b>{data['qual_rate']:.1f}%</b> от входящих)\n"
        f"• Нецелевой / спам / дубли: <b>{data['junk_count']} шт.</b>\n"
        f"• 🟢 <b>Выкуплено (WON):</b> <b>{data['won_count']} шт.</b> на сумму <b>{data['won_amount']:,.0f} ₽</b>\n"
        f"• 📈 <b>Конверсия в выкуп (CR Qual):</b> <b>{data['cr_qual']:.1f}%</b>\n"
        f"• 🟡 <b>Осталось в работе / доставке:</b> <b>{data['in_work_count']} шт.</b> ({data['in_work_amount']:,.0f} ₽)\n"
        f"• 🔴 <b>Отказы:</b> <b>{data['lose_count']} шт.</b> ({data['lose_amount']:,.0f} ₽)\n"
    )
    
    if data['in_work_breakdown']:
        text += "\n📦 <b>Заказы в работе по статусам:</b>\n"
        for st_name, st_val in data['in_work_breakdown'][:4]:
            text += f"• {html.escape(st_name)}: <b>{st_val['count']} шт.</b> ({st_val['amount']:,.0f} ₽)\n"
            
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "📈 Графики & Динамика")
@router.message(Command("charts"))
async def handle_charts(message: Message):
    wait_msg = await message.answer("⏳ Строю аналитические графики за 7 дней...")
    try:
        buf, stats = await get_7days_charts_and_stats()
        caption = (
            f"📈 <b>Аналитика динамики за 7 дней ({stats['start_date']} – {stats['end_date']})</b>\n\n"
            f"1️⃣ <b>Входящий поток:</b> Всего <b>{stats['total_orders_7d']} заказов</b> (в среднем <b>{stats['avg_daily_orders']:.1f} зак/день</b>)\n"
            f"2️⃣ <b>Качество трафика:</b> Средняя квалификация <b>{stats['avg_qual_rate']:.1f}%</b> (целевая планка: <b>95%</b>)\n"
            f"3️⃣ <b>Кассовая выручка WON:</b> <b>{stats['total_won_revenue_7d']:,.0f} ₽</b> (<b>{stats['total_won_count_7d']}</b> выкупленных заказов)\n\n"
            f"<i>* График 3 отражает фактические кассовые оплаты по дате закрытия сделки (WON).</i>"
        )
        photo_file = BufferedInputFile(buf.read(), filename="weekly_dynamics.png")
        await message.answer_photo(photo_file, caption=caption, parse_mode="HTML")
        await wait_msg.delete()
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
        await wait_msg.edit_text(f"❌ Ошибка генерации графиков: {e}")

@router.message(F.text == "⏳ Зависшие сделки (>48ч)")
@router.message(Command("pipeline"))
async def handle_pipeline(message: Message):
    wait_msg = await message.answer("⏳ Анализирую сделки в работе без движения более 48 часов...")
    summary = await get_pipeline_stuck_summary(min_hours=48)
    
    if not summary["breakdown"]:
        await wait_msg.edit_text("🎉 <b>Отлично!</b> В воронке нет сделок без движения более 48 часов.")
        return
        
    text = (
        f"⏳ <b>Зависшие заказы в работе (> 48ч без движения)</b>\n\n"
        f"📊 <b>Общий объем:</b>\n"
        f"• Зависло: <b>{summary['total_stuck_count']} сделок</b> на сумму <b>{summary['total_stuck_amount']:,.0f} ₽</b>\n"
        f"• Доля от всех заказов в работе: <b>{summary['stuck_share_cnt']:.1f}%</b> по кол-ву (<b>{summary['stuck_share_amt']:.1f}%</b> по сумме)\n\n"
        f"⚠️ <b>Структура по статусам (по убыванию суммы):</b>\n"
    )
    
    for item in summary["breakdown"]:
        s_name = html.escape(str(item['stage_name']))
        text += (
            f"• <b>{s_name}</b>\n"
            f"   <b>{item['count']} сделок</b> | <b>{item['amount']:,.0f} ₽</b> ({item['pct']:.1f}% от зависших)\n"
        )
        
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "🗓 Недельный отчет (7 дней)")
@router.message(Command("week"))
async def handle_week(message: Message):
    wait_msg = await message.answer("⏳ Формирую отчет за 7 полных закрытых дней...")
    now = get_now_msk()
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_7d = yesterday - timedelta(days=6)
    
    data = await get_funnel_summary(start_7d, yesterday)
    
    text = (
        f"🗓 <b>Недельный отчет CRM ({start_7d.strftime('%d.%m')} – {yesterday.strftime('%d.%m.%Y')})</b>\n\n"
        f"📥 <b>Воронка за 7 полных дней:</b>\n"
        f"• Всего заказов: <b>{data['total_count']} шт.</b> на <b>{data['total_amount']:,.0f} ₽</b>\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> (<b>{data['qual_rate']:.1f}%</b>)\n"
        f"• Нецелевой / спам / дубли: <b>{data['junk_count']} шт.</b>\n"
        f"• 🟢 <b>Выкуплено (WON):</b> <b>{data['won_count']} шт.</b> на <b>{data['won_amount']:,.0f} ₽</b>\n"
        f"• 📈 <b>Конверсия в выкуп (CR Qual):</b> <b>{data['cr_qual']:.1f}%</b>\n"
        f"• 🟡 <b>Остается в работе / доставке:</b> <b>{data['in_work_count']} шт.</b> ({data['in_work_amount']:,.0f} ₽)\n"
        f"• 🔴 <b>Отказы:</b> <b>{data['lose_count']} шт.</b> (потери: <b>{data['lose_amount']:,.0f} ₽</b>)\n"
    )
    
    if data['in_work_breakdown']:
        text += "\n📦 <b>Текущее распределение заказов в работе:</b>\n"
        for st_name, st_val in data['in_work_breakdown'][:4]:
            text += f"• {html.escape(st_name)}: <b>{st_val['count']} шт.</b> ({st_val['amount']:,.0f} ₽)\n"
            
    await wait_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text == "🛑 Причины отказов")
@router.message(Command("reasons"))
async def handle_reasons(message: Message):
    wait_msg = await message.answer("⏳ Собираю структуру отказов за последние 7 дней...")
    now = get_now_msk()
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_7d = yesterday - timedelta(days=6)
    
    data = await get_funnel_summary(start_7d, yesterday)
    
    text = (
        f"🛑 <b>Анализ причин отказов в CRM (За 7 закрытых дней)</b>\n"
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
