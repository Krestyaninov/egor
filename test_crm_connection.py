import os
import json
import urllib.request
import urllib.parse
import urllib.error

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
    data = None
    if params:
        data = json.dumps(params).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode('utf-8')}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== 1. Проверка доступных прав (Scope) ===")
    scope_info = call_b24("scope")
    print("Scopes:", json.dumps(scope_info, indent=2, ensure_ascii=False))

    print("\n=== 2. Проверка категорий (воронок) сделок ===")
    categories = call_b24("crm.dealcategory.list")
    print("Categories:", json.dumps(categories, indent=2, ensure_ascii=False))

    print("\n=== 3. Проверка источников (SOURCE) ===")
    sources = call_b24("crm.status.list", {"filter": {"ENTITY_ID": "SOURCE"}})
    if "result" in sources:
        print(f"Найдено источников: {len(sources['result'])}")
        for s in sources["result"][:10]:
            print(f"  - [{s.get('STATUS_ID')}] {s.get('NAME')}")
    else:
        print("Sources result:", sources)

    print("\n=== 4. Проверка последних сделок ===")
    deals = call_b24("crm.deal.list", {
        "order": {"DATE_CREATE": "DESC"},
        "select": ["ID", "TITLE", "STAGE_ID", "CATEGORY_ID", "OPPORTUNITY", "CURRENCY_ID", "DATE_CREATE", "UTM_SOURCE", "UTM_MEDIUM", "UTM_CAMPAIGN", "SOURCE_ID"],
        "start": 0
    })
    if "result" in deals:
        print(f"Всего сделок (примерная выборка/total): {deals.get('total')}")
        print("Последние 5 сделок:")
        for d in deals["result"][:5]:
            print(f"  ID {d.get('ID')}: {d.get('TITLE')} | {d.get('OPPORTUNITY')} {d.get('CURRENCY_ID')} | Воронка: {d.get('CATEGORY_ID')} | Стадия: {d.get('STAGE_ID')} | Источник: {d.get('SOURCE_ID')} | UTM: {d.get('UTM_SOURCE')}")
    else:
        print("Deals result:", deals)

if __name__ == "__main__":
    main()
