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
    print("=== Проверяем User Fields на портале ===")
    
    # 1. crm.userfield.list
    res_crm_uf = call_b24("crm.userfield.list")
    print("crm.userfield.list count:", len(res_crm_uf.get("result", [])))
    for uf in res_crm_uf.get("result", []):
        if "COLLECTION" in uf.get("FIELD_NAME", "").upper() or "UF_" in uf.get("FIELD_NAME", ""):
            print("  CRM UF:", uf.get("FIELD_NAME"), uf.get("USER_TYPE_ID"), uf.get("EDIT_FORM_LABEL"))

    # 2. Check catalog userfields if any
    # Let's test catalog.section.list with explicit select of UF_COLLECTION and UF_COLLECTION_DESCRIPTION
    res_sec = call_b24("catalog.section.list", {
        "filter": {"iblockId": 11},
        "select": ["id", "name", "code", "UF_COLLECTION", "UF_COLLECTION_DESCRIPTION", "UF_*"]
    })
    print("\ncatalog.section.list with UF_* select:")
    print(json.dumps(res_sec.get("result", {}).get("sections", [])[:3], indent=2, ensure_ascii=False))

    # 3. Check iblock section get / list if methods exist
    # Let's test methods via b24 documentation or common methods
    methods_to_test = [
        "userfield.list",
        "catalog.userfield.list",
        "iblock.section.list",
        "crm.productsection.get",
        "catalog.section.update"
    ]
    for m in methods_to_test:
        r = call_b24(m)
        print(f"Method {m} response:", "error" if "error" in r else "success")

if __name__ == "__main__":
    main()
