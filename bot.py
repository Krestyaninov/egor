import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_PROXY_URL
from handlers import router
from b24_client import b24
from analytics import get_now_msk, get_funnel_summary, get_categories_breakdown, get_pipeline_stuck_deals
from datetime import timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Хранилище chat_id подписчиков на дайджесты
SUBSCRIBED_CHATS = set()

async def send_morning_digest(bot: Bot):
    """Утренний дайджест в 09:00 МСК"""
    if not SUBSCRIBED_CHATS:
        return
    now = get_now_msk()
    yesterday = now - timedelta(days=1)
    data = await get_funnel_summary(yesterday, yesterday)
    stuck = await get_pipeline_stuck_deals()
    
    text = (
        f"🌅 <b>Утренний пульс CRM | Итоги за {yesterday.strftime('%d.%m.%Y')}</b>\n\n"
        f"📥 <b>Воронка вчера:</b>\n"
        f"• Всего заказов: <b>{data['total_count']} шт.</b> ({data['total_amount']:,.0f} ₽)\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> ({data['qual_rate']:.1f}%)\n"
        f"• Выкуплено (WON): <b>{data['won_count']} шт.</b> на <b>{data['won_amount']:,.0f} ₽</b>\n"
        f"• Конверсия (CR Qual): <b>{data['cr_qual']:.1f}%</b>\n\n"
        f"⏳ <b>Зависший пайплайн на утро:</b>\n"
        f"• Заказов в работе > 24ч: <b>{len(stuck)} сделок</b> (на <b>{sum(s['amount'] for s in stuck):,.0f} ₽</b>)\n"
    )
    
    for chat_id in SUBSCRIBED_CHATS:
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send morning digest to {chat_id}: {e}")

async def send_evening_digest(bot: Bot):
    """Вечерний срез в 21:00 МСК"""
    if not SUBSCRIBED_CHATS:
        return
    now = get_now_msk()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    data = await get_funnel_summary(today_start, now)
    categories = await get_categories_breakdown(data["won_deals"])
    
    total_profit = sum(c["profit"] for c in categories)
    
    text = (
        f"🌙 <b>Вечерний срез по категориям | {now.strftime('%d.%m.%Y')}</b>\n\n"
        f"🏆 <b>Выкуплено:</b> {data['won_count']} шт. на {data['won_amount']:,.0f} ₽ (Конверсия: {data['cr_qual']:.1f}%)\n"
        f"💰 <b>Расчетная чистая прибыль:</b> <b>+{total_profit:,.0f} ₽</b>\n\n"
        f"📱 <b>Топ категорий:</b>\n"
    )
    for c in categories[:4]:
        text += f"• <b>{c['category']}</b>: {c['count']} шт. | Выручка: {c['revenue']:,.0f} ₽ | ЧП: <b>+{c['profit']:,.0f} ₽</b>\n"
        
    if data['reasons']:
        top_reason = data['reasons'][0]
        text += f"\n🛑 <b>Главный отказ:</b> {top_reason[0]} ({top_reason[1]['count']} шт. на {top_reason[1]['amount']:,.0f} ₽)"

    for chat_id in SUBSCRIBED_CHATS:
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send evening digest to {chat_id}: {e}")

async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env!")
        return

    # Инициализация с прокси при наличии
    if TELEGRAM_PROXY_URL:
        session = AiohttpSession(proxy=TELEGRAM_PROXY_URL)
        bot = Bot(token=TELEGRAM_BOT_TOKEN, session=session)
        logger.info(f"Telegram Bot initialized using proxy: {TELEGRAM_PROXY_URL.split('@')[-1]}")
    else:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("Telegram Bot initialized directly without proxy.")

    dp = Dispatcher()
    dp.include_router(router)

    @dp.message.outer_middleware()
    async def track_chats_middleware(handler, event, data):
        if event.chat and event.chat.id:
            SUBSCRIBED_CHATS.add(event.chat.id)
        return await handler(event, data)

    # Настройка планировщика расписаний
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_morning_digest, CronTrigger(hour=9, minute=0), args=[bot])
    scheduler.add_job(send_evening_digest, CronTrigger(hour=21, minute=0), args=[bot])
    scheduler.start()

    logger.info("Запуск Telegram-бота Аналитик Егор (@egor_quapmi_bot)...")
    await bot.delete_webhook(drop_pending_updates=True)

    # Бесконечный цикл с авто-восстановлением при сетевых сбоях
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"Polling loop exception: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
