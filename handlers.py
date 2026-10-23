import logging
import html
from typing import Dict, Any, List, Optional
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)
from datetime import timedelta
from auth import auth_manager
from analytics import (
    get_now_msk,
    get_funnel_summary,
    get_pipeline_stuck_summary,
    get_7days_charts_and_stats,
    get_zero_deals_data,
    generate_zero_deals_chart,
    get_product_types_data,
    generate_product_types_chart,
    PRODUCT_CATEGORIES
)

logger = logging.getLogger(__name__)
router = Router()

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📊 Сегодня (Пульс)"), KeyboardButton(text="🌅 Вчера (Итоги)")],
        [KeyboardButton(text="📈 Графики & Динамика"), KeyboardButton(text="🗓 Недельный отчет (7 дней)")],
        [KeyboardButton(text="🏷 Продажи по товарам"), KeyboardButton(text="⭕️ Нулевые сделки")],
        [KeyboardButton(text="⏳ Зависшие сделки (>48ч)"), KeyboardButton(text="🛑 Причины отказов")]
    ]
    if auth_manager.is_admin(user_id):
        kb.append([KeyboardButton(text="⚙️ Доступы & Сотрудники")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Сгенерировать инвайт-пароль", callback_data="admin_gen_invite")],
        [InlineKeyboardButton(text="👥 Список сотрудников", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="📋 Активные инвайты", callback_data="admin_list_invites")],
        [InlineKeyboardButton(text="🗑 Отозвать доступ", callback_data="admin_revoke_menu")]
    ])

# --- Проверка доступа и обработка авторизации ---

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user_name = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    
    # 1. Проверяем, передан ли токен в /start <TOKEN>
    args = command.args
    if args:
        token = args.strip().upper()
        if auth_manager.use_invite_token(token, user_id, user_name, full_name):
            welcome = (
                f"✅ <b>Доступ успешно активирован!</b>\n\n"
                f"Добро пожаловать в команду, {html.escape(full_name)}!\n"
                f"Вам открыт доступ к корпоративной CRM-аналитике и воронке продаж.\n\n"
                f"👇 Выбирайте нужный отчет в меню ниже:"
            )
            await message.answer(welcome, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
            return
        elif not auth_manager.is_authorized(user_id):
            await message.answer("❌ <b>Неверный или уже использованный одноразовый пароль.</b>\nОбратитесь к администратору для получения нового приглашения.", parse_mode="HTML")
            return

    # 2. Если уже авторизован
    if auth_manager.is_authorized(user_id):
        role_label = "👑 Главный Администратор" if auth_manager.is_admin(user_id) else "👤 Авторизованный сотрудник"
        welcome_text = (
            f"👋 <b>Привет, {html.escape(full_name)}!</b>\n"
            f"Статус: <i>{role_label}</i>\n\n"
            f"🎯 <b>Доступные отчеты Аналитика Егора:</b>\n"
            f"• 📊 <b>Сегодня (Пульс):</b> Входящий поток, квалификация, выкуп и отказы день-в-день\n"
            f"• 🌅 <b>Вчера (Итоги):</b> Итоги прошедшего дня и конверсия в выкуп\n"
            f"• 📈 <b>Графики & Динамика:</b> 3 диаграммы по спросу, качеству трафика (цель 95%) и выручке WON\n"
            f"• 🗓 <b>Недельный отчет:</b> Сводка за полные 7 закрытых дней\n"
            f"• 🏷 <b>Продажи по товарам:</b> Воронка по типам (Apple vs Другие) за Вчера / Неделю / Месяц\n"
            f"• ⭕️ <b>Нулевые сделки:</b> Анализ лидов с 0 ₽ по дням (7 дн) и неделям (5 нед) с графиком\n"
            f"• ⏳ <b>Зависшие сделки (>48ч):</b> Структура заказов без движения по статусам и суммам\n"
            f"• 🛑 <b>Причины отказов:</b> Рейтинг потерь выручки с понятными причинами\n\n"
            f"👇 Выбирай нужный срез в меню:"
        )
        await message.answer(welcome_text, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
    else:
        # 3. Пользователь не авторизован
        no_access_text = (
            f"⛔️ <b>Доступ ограничен</b>\n\n"
            f"Этот бот содержит закрытую коммерческую аналитику компании.\n\n"
            f"🔑 <b>Для получения доступа:</b>\n"
            f"Отправьте в ответное сообщение <b>одноразовый пароль-приглашение</b> (6 символов), который вам предоставил руководитель.\n\n"
            f"🆔 <i>Ваш Telegram ID: <code>{user_id}</code></i>"
        )
        await message.answer(no_access_text, parse_mode="HTML")

# --- Общий фильтр текстовых сообщений для неавторизованных пользователей ---

@router.message(lambda msg: not auth_manager.is_authorized(msg.from_user.id))
async def handle_unauthorized_message(message: Message):
    text = (message.text or "").strip().upper()
    user_id = message.from_user.id
    user_name = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    
    # Пробуем проверить введенный текст как одноразовый пароль
    if len(text) == 6 and auth_manager.use_invite_token(text, user_id, user_name, full_name):
        welcome = (
            f"✅ <b>Пароль принят! Доступ успешно предоставлен.</b>\n\n"
            f"Добро пожаловать, {html.escape(full_name)}!\n"
            f"Вам открыт доступ ко всем отчетам CRM-аналитика.\n\n"
            f"👇 Выбирайте отчет в меню ниже:"
        )
        await message.answer(welcome, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
    else:
        no_access_text = (
            f"⛔️ <b>Неверный пароль или доступ закрыт</b>\n\n"
            f"Введенный код не найден или уже был активирован.\n"
            f"Пожалуйста, запросите одноразовый пароль у администратора.\n\n"
            f"🆔 <i>Ваш Telegram ID: <code>{user_id}</code></i>"
        )
        await message.answer(no_access_text, parse_mode="HTML")

# --- Административная панель и управление доступами ---

@router.message(F.text == "⚙️ Доступы & Сотрудники")
@router.message(Command("admin"))
async def handle_admin_panel(message: Message):
    user_id = message.from_user.id
    if not auth_manager.is_admin(user_id):
        await message.answer("⛔️ Эта функция доступна только главному администратору.")
        return
        
    users = auth_manager.get_all_authorized_users()
    invites = auth_manager.get_active_invites()
    
    text = (
        f"⚙️ <b>Панель управления доступами</b>\n\n"
        f"👥 Авторизованных сотрудников: <b>{len(users)}</b>\n"
        f"🔑 Активных неиспользованных инвайтов: <b>{len(invites)}</b>\n\n"
        f"Выберите действие ниже:"
    )
    await message.answer(text, reply_markup=get_admin_inline_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_gen_invite")
async def cb_gen_invite(call: CallbackQuery):
    if not auth_manager.is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
        
    token = auth_manager.generate_invite_token(call.from_user.id)
    bot_user = await call.bot.get_me()
    invite_link = f"https://t.me/{bot_user.username}?start={token}"
    
    text = (
        f"🔑 <b>Новый одноразовый пароль создан!</b>\n\n"
        f"Код: <code>{token}</code>\n\n"
        f"🔗 <b>Прямая ссылка для входа в 1 клик:</b>\n"
        f"{invite_link}\n\n"
        f"<i>Отправьте этот код или ссылку сотруднику. Пароль одноразовый: после первого входа он будет закреплен за сотрудником и сгорит для повторного использования.</i>"
    )
    await call.message.edit_text(text, reply_markup=get_admin_inline_kb(), parse_mode="HTML")
    await call.answer("Пароль успешно сгенерирован!")

@router.callback_query(F.data == "admin_list_users")
async def cb_list_users(call: CallbackQuery):
    if not auth_manager.is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
        
    users = auth_manager.get_all_authorized_users()
    text = f"👥 <b>Список авторизованных сотрудников ({len(users)} чел):</b>\n\n"
    
    for u in users.values():
        role_ico = "👑" if u.get("role") == "admin" else "👤"
        uname = f"(@{u['username']})" if u.get("username") else ""
        text += f"{role_ico} <b>{html.escape(u.get('full_name', 'Сотрудник'))}</b> {uname}\n"
        text += f"   ID: <code>{u['user_id']}</code> | Добавлен: {u.get('added_at', '—')}\n\n"
        
    await call.message.edit_text(text, reply_markup=get_admin_inline_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin_list_invites")
async def cb_list_invites(call: CallbackQuery):
    if not auth_manager.is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
        
    invites = auth_manager.get_active_invites()
    bot_user = await call.bot.get_me()
    
    if not invites:
        text = "📋 <b>Нет активных неиспользованных инвайтов.</b>\nНажмите <i>«Сгенерировать инвайт-пароль»</i> для создания."
    else:
        text = f"📋 <b>Активные одноразовые пароли ({len(invites)} шт):</b>\n\n"
        for inv in invites:
            link = f"https://t.me/{bot_user.username}?start={inv['token']}"
            text += f"• Код: <code>{inv['token']}</code> (создан {inv['created_at']})\n  {link}\n\n"
            
    await call.message.edit_text(text, reply_markup=get_admin_inline_kb(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "admin_revoke_menu")
async def cb_revoke_menu(call: CallbackQuery):
    if not auth_manager.is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
        
    users = auth_manager.get_all_authorized_users()
    non_admins = [u for u in users.values() if u.get("role") != "admin"]
    
    if not non_admins:
        await call.message.edit_text("👥 Нет сотрудников для удаления (кроме главного администратора).", reply_markup=get_admin_inline_kb())
        await call.answer()
        return
        
    kb_buttons = []
    for u in non_admins:
        name = u.get("full_name") or f"ID {u['user_id']}"
        kb_buttons.append([InlineKeyboardButton(text=f"❌ Отозвать у {name[:20]}", callback_data=f"revoke_{u['user_id']}")])
    kb_buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_back")])
    
    await call.message.edit_text("Выберите сотрудника, доступ которого требуется аннулировать:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await call.answer()

@router.callback_query(F.data.startswith("revoke_"))
async def cb_do_revoke(call: CallbackQuery):
    if not auth_manager.is_admin(call.from_user.id):
        await call.answer("Нет прав", show_alert=True)
        return
        
    target_id = int(call.data.replace("revoke_", ""))
    if auth_manager.revoke_user_access(target_id):
        await call.answer(f"Доступ сотрудника {target_id} успешно отозван!", show_alert=True)
    else:
        await call.answer("Не удалось отозвать доступ", show_alert=True)
        
    await handle_admin_panel(call.message)

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(call: CallbackQuery):
    if not auth_manager.is_admin(call.from_user.id):
        return
    await handle_admin_panel(call.message)
    await call.answer()

# --- Аналитические отчеты для авторизованных пользователей ---

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

# =====================================================================
# НОВЫЙ БЛОК: Нулевые сделки (кнопки, форматирование, графики)
# =====================================================================

def get_zero_deals_kb(current_mode: str) -> InlineKeyboardMarkup:
    btn_7d_text = "• 📅 7 дней (по дням) •" if current_mode == "7days" else "📅 7 дней (по дням)"
    btn_5w_text = "• 🗓 5 недель •" if current_mode == "5weeks" else "🗓 5 недель"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=btn_7d_text, callback_data="zero_mode_7days"),
            InlineKeyboardButton(text=btn_5w_text, callback_data="zero_mode_5weeks")
        ],
        [
            InlineKeyboardButton(text="📈 Показать график динамики", callback_data=f"zero_chart_{current_mode}")
        ]
    ])

def format_zero_deals_text(data: Dict[str, Any]) -> str:
    period_label = "7 полных дней (до вчера)" if data["mode"] == "7days" else "5 недель (до вчера)"
    text = (
        f"⭕️ <b>Анализ сделок с суммой 0 ₽ (без спама)</b>\n"
        f"Период: <b>{period_label}</b> ({data['start_date']} – {data['end_date']})\n\n"
        f"<i>Правило ведения CRM: менеджеры обязаны вносить товар и фиксировать сумму даже при отказе. Нулевые сделки — индикатор необработанных заказов или нарушений регламента.</i>\n\n"
        f"📊 <b>Сводные показатели:</b>\n"
        f"• Квалифицированных сделок: <b>{data['total_qual']} шт.</b>\n"
        f"• Сделок с 0 ₽: <b>{data['total_zero']} шт.</b> (<b>{data['overall_rate']:.1f}%</b> от базы)\n"
        f"• Исключено спама/дублей/нецелевых: <b>{data['total_junk']} шт.</b>\n\n"
        f"📅 <b>Динамика среза:</b>\n"
    )
    for it in data["items"]:
        text += f"• {it['label']}: <b>{it['zero']} шт.</b> с 0 ₽ из {it['qual']} квал. (<b>{it['rate']:.1f}%</b>)\n"
        
    return text

@router.message(F.text == "⭕️ Нулевые сделки")
@router.message(Command("zero"))
async def handle_zero_deals(message: Message):
    wait_msg = await message.answer("⏳ Анализирую сделки с 0 суммой за последние 7 дней...")
    try:
        data = await get_zero_deals_data(mode="7days")
        text = format_zero_deals_text(data)
        await wait_msg.edit_text(text, reply_markup=get_zero_deals_kb("7days"), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error handling zero deals: {e}")
        await wait_msg.edit_text(f"❌ Ошибка загрузки данных: {e}")

@router.callback_query(F.data.startswith("zero_mode_"))
async def cb_zero_mode(call: CallbackQuery):
    mode = call.data.replace("zero_mode_", "")
    await call.answer("Загружаю данные...")
    try:
        data = await get_zero_deals_data(mode=mode)
        text = format_zero_deals_text(data)
        await call.message.edit_text(text, reply_markup=get_zero_deals_kb(mode), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error switching zero mode: {e}")
        await call.message.edit_text(f"❌ Ошибка обновления: {e}")

@router.callback_query(F.data.startswith("zero_chart_"))
async def cb_zero_chart(call: CallbackQuery):
    mode = call.data.replace("zero_chart_", "")
    await call.answer("Генерирую диаграмму...")
    try:
        data = await get_zero_deals_data(mode=mode)
        buf = generate_zero_deals_chart(data)
        caption = (
            f"📈 <b>График динамики нулевых сделок ({data['mode']})</b>\n\n"
            f"• Всего квалифицированных: <b>{data['total_qual']} шт.</b>\n"
            f"• Нулевых сделок: <b>{data['total_zero']} шт.</b> (<b>{data['overall_rate']:.1f}%</b>)\n\n"
            f"<i>Столбцы (синие) — количество сделок с 0 ₽, линия (красная) — доля от квалифицированных.</i>"
        )
        photo_file = BufferedInputFile(buf.read(), filename="zero_deals_chart.png")
        await call.message.answer_photo(photo_file, caption=caption, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error generating zero chart: {e}")
        await call.message.answer(f"❌ Ошибка генерации графика: {e}")

# =====================================================================
# НОВЫЙ БЛОК: Аналитика по типам товаров (Apple vs Другие)
# =====================================================================

def get_product_types_kb(current_period: str) -> InlineKeyboardMarkup:
    def mark(p: str, label: str) -> str:
        return f"• {label} •" if current_period == p else label
        
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=mark("yesterday", "🌅 Вчера"), callback_data="prod_p_yesterday"),
            InlineKeyboardButton(text=mark("this_week", "🗓 Тек. нед"), callback_data="prod_p_this_week"),
            InlineKeyboardButton(text=mark("prev_week", "📅 Прошлая нед"), callback_data="prod_p_prev_week")
        ],
        [
            InlineKeyboardButton(text=mark("this_month", "📆 Тек. месяц"), callback_data="prod_p_this_month"),
            InlineKeyboardButton(text=mark("prev_month", "🗂 Прошлый месяц"), callback_data="prod_p_prev_month")
        ],
        [
            InlineKeyboardButton(text="📈 Показать график среза", callback_data=f"prod_chart_{current_period}")
        ]
    ])

def format_product_types_text(data: Dict[str, Any]) -> str:
    title = data["title"]
    stats = data["stats"]
    total_deals = data["total_deals"]
    target_deals = data["total_target_deals"]
    
    text = (
        f"🏷 <b>Воронка по типам товаров | {title}</b>\n"
        f"<i>Группы: «Товары» и «Комплектующие» (квалифицированные лиды)</i>\n\n"
        f"📥 Всего квал. заказов: <b>{total_deals} шт.</b> (из них с целевыми товарами: <b>{target_deals} шт.</b>)\n\n"
    )
    
    CAT_ICONS = {
        "Смартфоны": "📱",
        "Планшеты": "📟",
        "Ноутбуки": "💻",
        "Смарт-часы": "⌚️",
        "Наушники": "🎧",
        "Другие товары": "📦"
    }
    
    for cat in PRODUCT_CATEGORIES:
        icon = CAT_ICONS.get(cat, "🔹")
        text += f"{icon} <b>{cat}:</b>\n"
        for brand in ["Apple", "Другие"]:
            s = stats[cat][brand]
            if s["deals"] > 0:
                text += (
                    f"   • {brand}: <b>{s['deals']} лид.</b> | "
                    f"Выкуп: <b>{s['cr']:.1f}%</b> ({s['won']} шт) | "
                    f"Ср. чек: <b>{s['avg_check']:,.0f} ₽</b> | "
                    f"Сумма: <b>{s['amount']:,.0f} ₽</b>\n"
                )
            else:
                text += f"   • {brand}: <i>нет лидов</i>\n"
        text += "\n"
        
    return text

@router.message(F.text == "🏷 Продажи по товарам")
@router.message(Command("products"))
async def handle_product_types(message: Message):
    wait_msg = await message.answer("⏳ Собираю продажи по товарным группам за вчера...")
    try:
        data = await get_product_types_data(period="yesterday")
        text = format_product_types_text(data)
        await wait_msg.edit_text(text, reply_markup=get_product_types_kb("yesterday"), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error handling product types: {e}")
        await wait_msg.edit_text(f"❌ Ошибка выгрузки: {e}")

@router.callback_query(F.data.startswith("prod_p_"))
async def cb_product_period(call: CallbackQuery):
    period = call.data.replace("prod_p_", "")
    await call.answer("Загружаю срез...")
    try:
        data = await get_product_types_data(period=period)
        text = format_product_types_text(data)
        await call.message.edit_text(text, reply_markup=get_product_types_kb(period), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error switching product period: {e}")
        await call.message.edit_text(f"❌ Ошибка обновления: {e}")

@router.callback_query(F.data.startswith("prod_chart_"))
async def cb_product_chart(call: CallbackQuery):
    period = call.data.replace("prod_chart_", "")
    await call.answer("Генерирую диаграмму...")
    try:
        data = await get_product_types_data(period=period)
        buf = generate_product_types_chart(data)
        caption = (
            f"📈 <b>Аналитика по типам товаров (Apple vs Другие)</b>\n"
            f"Период: <b>{data['title']}</b>\n\n"
            f"1️⃣ <b>Лиды:</b> Сравнение объема входящего спроса\n"
            f"2️⃣ <b>Конверсия:</b> Процент выкупа (% WON от квал. сделок)\n"
            f"3️⃣ <b>Средний чек:</b> Средняя сумма позиций товара в сделке"
        )
        photo_file = BufferedInputFile(buf.read(), filename="product_types_chart.png")
        await call.message.answer_photo(photo_file, caption=caption, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error generating product chart: {e}")
        await call.message.answer(f"❌ Ошибка создания графика: {e}")

