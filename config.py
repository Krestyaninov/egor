import os
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").rstrip("/") + "/"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CATALOG_IBLOCK_ID = int(os.getenv("CATALOG_IBLOCK_ID", "11"))

# Полный маппинг стадий воронки CRM (с типами для сквозной аналитики маркетинга)
STAGE_MAP = {
    # 1. В работе (Промежуточный пайплайн)
    "NEW": {"name": "Новый заказ", "type": "IN_WORK"},
    "UC_4XBQ8T": {"name": "Взят в работу (до 3 дн)", "type": "IN_WORK"},
    "UC_UIY3QD": {"name": "Взят в работу (3-7 дн)", "type": "IN_WORK"},
    "UC_IJVZ80": {"name": "Предзаказ (новинка)", "type": "IN_WORK"},
    "UC_NE86CK": {"name": "Ожидание поступления", "type": "IN_WORK"},
    "UC_MBOUEP": {"name": "Недозвон", "type": "IN_WORK"},
    "UC_TQ17HG": {"name": "Счёт выставлен", "type": "IN_WORK"},
    "UC_23P6ED": {"name": "Ожидание оплаты", "type": "IN_WORK"},
    "UC_4Z9LSW": {"name": "Заказ на сборку", "type": "IN_WORK"},
    "UC_P5ATJA": {"name": "Сборка заказа", "type": "IN_WORK"},
    "UC_4XVAO6": {"name": "Готов к отгрузке", "type": "IN_WORK"},
    "UC_9QBZCS": {"name": "Доставка курьером", "type": "IN_WORK"},
    "UC_KK1PT6": {"name": "Самовывоз из магазина", "type": "IN_WORK"},
    
    # 2. Успех (Выкуп)
    "WON": {"name": "Заказ выкуплен", "type": "WON"},
    
    # 3. Нецелевые / Спам / Ошибки (Исключаются из квалифицированных)
    "APOLOGY": {"name": "Спам", "type": "JUNK"},
    "UC_Q7TYRN": {"name": "Внутренние Спам чаты", "type": "JUNK"},
    "UC_OL2S30": {"name": "Дубль заказа", "type": "JUNK"},
    "UC_I3TUCW": {"name": "Неверный номер", "type": "JUNK"},
    "2": {"name": "Нецелевой клиент", "type": "JUNK"},
    "3": {"name": "Чёрный список (ЧС)", "type": "JUNK"},
    
    # 4. Квалифицированные отказы (Реальные причины срывов)
    "LOSE": {"name": "Нет в наличии", "type": "LOSE"},
    "UC_RRQO4D": {"name": "Не устроила цена / нашел дешевле", "type": "LOSE"},
    "UC_LWROSL": {"name": "Неактуально / передумал", "type": "LOSE"},
    "UC_IVB3AA": {"name": "Не берет трубку / не отвечает", "type": "LOSE"},
    "1": {"name": "Купил в рознице оффлайн", "type": "LOSE"},
    "4": {"name": "Оплата частями (Долями/Сплит)", "type": "LOSE"},
    "5": {"name": "Возврат товара", "type": "LOSE"},
    "6": {"name": "Не устроили условия доставки", "type": "LOSE"},
    "UC_3JZ3IX": {"name": "Недозвон по заявке", "type": "LOSE"},
    "UC_2VQFLC": {"name": "Уже купил у нас ранее", "type": "LOSE"},
}

# Бенчмарк маржинальности по товарным категориям (%)
CATEGORY_MARGIN_BENCHMARKS = {
    "Dyson / Красота": 0.205,         # 20.5%
    "Роботы и пылесосы": 0.163,       # 16.3%
    "Наушники / Акустика": 0.180,     # 18.0%
    "Умные очки / Гаджеты": 0.220,    # 22.0%
    "Android Флагманы": 0.115,        # 11.5%
    "Телевизоры": 0.090,              # 9.0%
    "MacBook Pro / Studio": 0.095,    # 9.5%
    "MacBook Air & Neo": 0.075,       # 7.5%
    "Apple iPad": 0.080,              # 8.0%
    "Apple Watch / Garmin": 0.090,    # 9.0%
    "Игровые приставки / VR": 0.120,  # 12.0%
    "Android Масс-маркет": 0.085,     # 8.5%
    "Apple iPhone": 0.036,            # 3.6%
    "Прочее": 0.070                   # 7.0%
}
