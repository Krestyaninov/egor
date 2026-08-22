from datetime import datetime, timezone, timedelta
import json
from b24_client import b24

# МСК таймзона
MSK_TZ = timezone(timedelta(hours=3))

STAGE_MAP = {
    "NEW": {"name": "Новый заказ", "type": "IN_WORK"},
    "UC_4XBQ8T": {"name": "Взят в работу до 3-х дней", "type": "IN_WORK"},
    "UC_UIY3QD": {"name": "Взят в работу 3-7 дней", "type": "IN_WORK"},
    "UC_IJVZ80": {"name": "Предзаказ (новинка)", "type": "IN_WORK"},
    "UC_NE86CK": {"name": "Ожидание поступления", "type": "IN_WORK"},
    "UC_MBOUEP": {"name": "Недозвон", "type": "IN_WORK"},
    "UC_TQ17HG": {"name": "Счёт выставлен", "type": "IN_WORK"},
    "UC_23P6ED": {"name": "Ожидание оплаты", "type": "IN_WORK"},
    "UC_4Z9LSW": {"name": "Заказ на сборку", "type": "IN_WORK"},
    "UC_P5ATJA": {"name": "Сборка заказа", "type": "IN_WORK"},
    "UC_4XVAO6": {"name": "Готов к отгрузке", "type": "IN_WORK"},
    "UC_9QBZCS": {"name": "Доставка", "type": "IN_WORK"},
    "UC_KK1PT6": {"name": "Самовывоз", "type": "IN_WORK"},
    "WON": {"name": "Заказ выкуплен", "type": "WON"},
    # Мусор / Нецелевые
    "APOLOGY": {"name": "Спам", "type": "JUNK"},
    "UC_Q7TYRN": {"name": "Внутренние Спам чаты", "type": "JUNK"},
    "UC_OL2S30": {"name": "Дубль", "type": "JUNK"},
    "UC_I3TUCW": {"name": "Неверный номер", "type": "JUNK"},
    "2": {"name": "Не целевой клиент", "type": "JUNK"},
    "3": {"name": "ЧС", "type": "JUNK"},
    # Реальные отказы
    "LOSE": {"name": "Нет в наличии", "type": "LOSE"},
    "UC_RRQO4D": {"name": "Не устроила цена", "type": "LOSE"},
    "UC_LWROSL": {"name": "Неактуально", "type": "LOSE"},
    "UC_IVB3AA": {"name": "Не берет трубку / не отвечает", "type": "LOSE"},
    "1": {"name": "Купил в рознице", "type": "LOSE"},
    "4": {"name": "Ванта/Долями/Сплит", "type": "LOSE"},
    "5": {"name": "Возврат", "type": "LOSE"},
    "6": {"name": "Условия доставки", "type": "LOSE"},
    "UC_3JZ3IX": {"name": "НДЗ по заявке OLD", "type": "LOSE"},
    "UC_2VQFLC": {"name": "Уже купил у нас OLD", "type": "LOSE"},
}

import asyncio
async def test():
    now = datetime(2026, 8, 21, 21, 30, tzinfo=MSK_TZ)
    start_str = "2026-08-21T00:00:00+03:00"
    end_str = "2026-08-21T23:59:59+03:00"
    deals = await b24.get_deals_by_date(start_str, end_str)
    
    total_cnt = len(deals)
    total_amt = sum(float(d.get("OPPORTUNITY") or 0) for d in deals)
    
    junk_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "JUNK"]
    junk_cnt = len(junk_deals)
    junk_amt = sum(float(d.get("OPPORTUNITY") or 0) for d in junk_deals)
    
    qual_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") != "JUNK"]
    qual_cnt = len(qual_deals)
    qual_amt = sum(float(d.get("OPPORTUNITY") or 0) for d in qual_deals)
    qual_rate = (qual_cnt / total_cnt * 100) if total_cnt > 0 else 0
    
    won_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "WON"]
    won_cnt = len(won_deals)
    won_amt = sum(float(d.get("OPPORTUNITY") or 0) for d in won_deals)
    
    in_work_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "IN_WORK"]
    in_work_cnt = len(in_work_deals)
    in_work_amt = sum(float(d.get("OPPORTUNITY") or 0) for d in in_work_deals)
    
    lose_deals = [d for d in deals if STAGE_MAP.get(d.get("STAGE_ID"), {}).get("type") == "LOSE"]
    lose_cnt = len(lose_deals)
    lose_amt = sum(float(d.get("OPPORTUNITY") or 0) for d in lose_deals)
    
    cr_qual = (won_cnt / qual_cnt * 100) if qual_cnt > 0 else 0
    
    print(f"=== СТАТИСТИКА ЗА 21.08.2026 ===")
    print(f"• Всего входящих: {total_cnt} шт. на {total_amt:,.0f} ₽")
    print(f"• Нецелевой/спам/дубли: {junk_cnt} шт. на {junk_amt:,.0f} ₽")
    print(f"• Квалифицированы: {qual_cnt} шт. на {qual_amt:,.0f} ₽ ({qual_rate:.1f}% от входящих)")
    print(f"• Выкуплено (WON): {won_cnt} шт. на {won_amt:,.0f} ₽")
    print(f"• Конверсия в выкуп (от Qual): {cr_qual:.1f}%")
    print(f"• В работе / доставке: {in_work_cnt} шт. на {in_work_amt:,.0f} ₽")
    print(f"• Отказы: {lose_cnt} шт. на {lose_amt:,.0f} ₽")
    
    print("\n--- Детализация 'В работе' ---")
    in_work_by_st = {}
    for d in in_work_deals:
        st = d.get("STAGE_ID")
        name = STAGE_MAP.get(st, {}).get("name", st)
        in_work_by_st[name] = in_work_by_st.get(name, 0) + 1
    for k, v in in_work_by_st.items():
        print(f"  - {k}: {v} шт.")

    print("\n--- Детализация 'Отказы' ---")
    lose_by_st = {}
    for d in lose_deals:
        st = d.get("STAGE_ID")
        name = STAGE_MAP.get(st, {}).get("name", st)
        lose_by_st[name] = lose_by_st.get(name, 0) + 1
    for k, v in lose_by_st.items():
        print(f"  - {k}: {v} шт.")

asyncio.run(test())
