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
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        return {"http_error": e.code, "body": err_body}
    except Exception as e:
        return {"error": str(e)}

def main():
    sec_id = 202
    
    # 1. Update with iblockId + UF fields
    res = call_b24("catalog.section.update", {
        "id": sec_id,
        "fields": {
            "iblockId": 11,
            "name": "Товары для красоты",
            "UF_COLLECTION": "Техника для красоты Dyson",
            "UF_COLLECTION_DESCRIPTION": "Оригинальные стайлеры и фены Dyson в наличии. Выгода при оплате наличными. Экспресс-доставка по Москве за 2-3 часа. Официальная гарантия 1 год."
        }
    })
    print("catalog.section.update with UF fields:", json.dumps(res, indent=2, ensure_ascii=False))

    # 2. Get section after update
    sec_after = call_b24("catalog.section.get", {"id": sec_id})
    print("\nРаздел 202 после обновления:", json.dumps(sec_after, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
