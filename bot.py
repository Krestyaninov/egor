import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_PROXY_URL
from handlers import router
from auth import auth_manager
from analytics import (
    get_now_msk,
    get_funnel_summary,
    get_pipeline_stuck_summary,
    get_7days_charts_and_stats
)
from datetime import timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def send_morning_digest(bot: Bot):
    """Утренний пульс CRM в 09:00 МСК: отправка только авторизованным сотрудникам"""
    target_chats = auth_manager.get_authorized_chat_ids()
    if not target_chats:
        logger.info("No authorized users for morning digest.")
        return

    now = get_now_msk()
    yesterday = now - timedelta(days=1)
    
    # 1. Воронка вчера
    data = await get_funnel_summary(yesterday, yesterday)
    
    # 2. Зависшие сделки (>48ч)
    stuck_summary = await get_pipeline_stuck_summary(min_hours=48)
    
    # 3. Графики за 7 дней
    chart_buf, chart_stats = await get_7days_charts_and_stats()
    
    caption_digest = (
        f"🌅 <b>Утренний пульс CRM | {now.strftime('%d.%m.%Y')}</b>\n\n"
        f"📥 <b>Итоги за вчера ({yesterday.strftime('%d.%m')}):</b>\n"
        f"• Создано: <b>{data['total_count']} шт.</b> ({data['total_amount']:,.0f} ₽)\n"
        f"• Квалифицированы: <b>{data['qual_count']} шт.</b> ({data['qual_rate']:.1f}%)\n"
        f"• 🟢 Выкуплено: <b>{data['won_count']} шт.</b> на <b>{data['won_amount']:,.0f} ₽</b>\n"
        f"• 📈 Конверсия (CR Qual): <b>{data['cr_qual']:.1f}%</b>\n\n"
        f"⏳ <b>Зависший пайплайн (> 48ч без движения):</b>\n"
        f"• Зависло: <b>{stuck_summary['total_stuck_count']} сделок</b> на <b>{stuck_summary['total_stuck_amount']:,.0f} ₽</b> "
        f"({stuck_summary['stuck_share_cnt']:.1f}% от всех заказов в работе)\n\n"
        f"📊 <i>Ниже прикреплены 3 графика динамики за последние 7 дней.</i>"
    )

    photo_bytes = chart_buf.read()
    for chat_id in target_chats:
        try:
            photo_file = BufferedInputFile(photo_bytes, filename="morning_digest.png")
            await bot.send_photo(chat_id, photo_file, caption=caption_digest, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send morning digest to {chat_id}: {e}")

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

    # Настройка планировщика расписаний (только утренний дайджест в 09:00)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_morning_digest, CronTrigger(hour=9, minute=0), args=[bot])
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
