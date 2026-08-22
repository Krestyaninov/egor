import os
import json
import urllib.request

# Чтение .env
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
if not WEBHOOK_URL.endswith('/'):
    WEBHOOK_URL += '/'

def call_b24(method: str, params: dict = None):
    url = f"{WEBHOOK_URL}{method}.json"
    data = json.dumps(params or {}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        return {"http_error": e.code, "body": err_body}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== Проверяем наличие себестоимости и закупочных цен в сделках CRM ===")
    
    # 1. Получаем недавнюю выкупленную сделку (WON)
    res = call_b24("crm.deal.list", {
        "order": {"DATE_CREATE": "DESC"},
        "filter": {"STAGE_ID": "WON"},
        "select": ["ID", "TITLE", "OPPORTUNITY", "DATE_CREATE"],
        "start": 0
    })
    deals = res.get("result", [])
    print(f"Найдено выкупленных сделок: {len(deals)}")
    
    if deals:
        d = deals[0]
        did = d["ID"]
        print(f"\nПроверяем сделку ID {did} ({d.get('TITLE')}, {d.get('OPPORTUNITY')} ₽):")
        
        # Получаем товарные позиции
        prows = call_b24("crm.deal.productrows.get", {"id": did})
        print("crm.deal.productrows.get:")
        print(json.dumps(prows, indent=2, ensure_ascii=False))

        # Если есть PRODUCT_ID, проверяем карточку товара crm.product.get
        rows = prows.get("result", [])
        if rows and rows[0].get("PRODUCT_ID"):
            pid = rows[0]["PRODUCT_ID"]
            prod_info = call_b24("crm.product.get", {"id": pid})
            print(f"\ncrm.product.get для товара {pid}:")
            print(json.dumps(prod_info, indent=2, ensure_ascii=False))

            # Проверим цены catalog.price.list
            prices = call_b24("catalog.price.list", {"filter": {"productId": pid}})
            print(f"\ncatalog.price.list для товара {pid}:")
            print(json.dumps(prices, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
