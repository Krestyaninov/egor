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
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== Проверка методов для разделов и пользовательских полей ===")
    
    # 1. catalog.section.get
    sec_get = call_b24("catalog.section.get", {"id": 199})
    print("catalog.section.get (199):", json.dumps(sec_get, indent=2, ensure_ascii=False))

    # 2. crm.productsection.fields
    crm_sec_fields = call_b24("crm.productsection.fields")
    print("\ncrm.productsection.fields:", json.dumps(crm_sec_fields, indent=2, ensure_ascii=False))

    # 3. crm.productsection.list
    crm_sec_list = call_b24("crm.productsection.list", {
        "order": {"ID": "ASC"},
        "filter": {"CATALOG_ID": 11},
        "select": ["*", "UF_*"]
    })
    print("\ncrm.productsection.list sample:", json.dumps(crm_sec_list.get("result", [])[:2], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
