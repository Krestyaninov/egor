import asyncio
from b24_client import b24
from datetime import datetime, timedelta, timezone

MSK_TZ = timezone(timedelta(hours=3))

async def test_won_detection():
    # За последние 14 дней
    start_str = "2026-08-16T00:00:00+03:00"
    end_str = "2026-08-30T23:59:59+03:00"
    
    # 1. По фильтру STAGE_ID: WON
    res = await b24.call("crm.deal.list", {
        "filter": {
            "STAGE_ID": "WON",
            ">=DATE_MODIFY": start_str,
            "<=DATE_MODIFY": end_str
        },
        "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSEDATE"]
    })
    deals_by_modify = res.get("result", [])
    print(f"Сделок WON по DATE_MODIFY: {len(deals_by_modify)}")
    
    by_day_modify = {}
    for d in deals_by_modify:
        m_day = (d.get("DATE_MODIFY") or "")[:10]
        by_day_modify[m_day] = by_day_modify.get(m_day, 0) + float(d.get("OPPORTUNITY") or 0)
        
    print("Выручка по DATE_MODIFY:")
    for k in sorted(by_day_modify.keys()):
        print(f"  {k}: {by_day_modify[k]:,.0f} ₽")

    # 2. По CLOSEDATE
    res_close = await b24.call("crm.deal.list", {
        "filter": {
            "STAGE_ID": "WON",
            ">=CLOSEDATE": start_str,
            "<=CLOSEDATE": end_str
        },
        "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSEDATE"]
    })
    deals_by_close = res_close.get("result", [])
    print(f"\nСделок WON по CLOSEDATE: {len(deals_by_close)}")
    by_day_close = {}
    for d in deals_by_close:
        c_day = (d.get("CLOSEDATE") or "")[:10]
        by_day_close[c_day] = by_day_close.get(c_day, 0) + float(d.get("OPPORTUNITY") or 0)
    print("Выручка по CLOSEDATE:")
    for k in sorted(by_day_close.keys()):
        print(f"  {k}: {by_day_close[k]:,.0f} ₽")

asyncio.run(test_won_detection())
