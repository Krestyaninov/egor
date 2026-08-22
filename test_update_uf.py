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
    print("=== Тестируем обновление раздела с UF-полями ===")
    
    # Попробуем прочитать текущий раздел (например, 202 - Товары для красоты)
    sec_id = 202
    sec_info = call_b24("catalog.section.get", {"id": sec_id})
    print("Текущие данные раздела 202:")
    print(json.dumps(sec_info, indent=2, ensure_ascii=False))

    # Пробуем вызвать catalog.section.update с UF_полями
    test_update = call_b24("catalog.section.update", {
        "id": sec_id,
        "fields": {
            "name": "Товары для красоты",
            "UF_COLLECTION": "Техника для красоты Dyson",
            "UF_COLLECTION_DESCRIPTION": "Оригинальные стайлеры и фены Dyson в наличии. Выгода при оплате наличными. Экспресс-доставка по Москве за 2-3 часа. Официальная гарантия."
        }
    })
    print("\nРезультат catalog.section.update с UF-полями:")
    print(json.dumps(test_update, indent=2, ensure_ascii=False))

    # Проверим, появились ли поля
    sec_after = call_b24("catalog.section.get", {"id": sec_id})
    print("\nДанные раздела 202 после обновления:")
    print(json.dumps(sec_after, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
