import os
import json
import urllib.request

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
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== Проверка полей закрытых сделок (WON) ===")
    res = call_b24("crm.deal.list", {
        "order": {"DATE_MODIFY": "DESC"},
        "filter": {"STAGE_ID": "WON"},
        "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSEDATE", "CLOSED"],
        "start": 0
    })
    deals = res.get("result", [])
    print(f"Выгружено недавних WON сделок: {len(deals)}")
    if deals:
        print("\nПримеры WON сделок:")
        for d in deals[:5]:
            print(f"ID: {d['ID']} | Сумма: {float(d.get('OPPORTUNITY') or 0):,.0f} ₽ | Создан: {d.get('DATE_CREATE')} | Изменен: {d.get('DATE_MODIFY')} | CLOSEDATE: {d.get('CLOSEDATE')}")

if __name__ == "__main__":
    main()
