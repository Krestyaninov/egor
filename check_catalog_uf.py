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
    print("=== 1. Проверяем поля разделов в каталоге (iblockId: 11) ===")
    
    # 1. Fetch sample sections with all fields
    res = call_b24("catalog.section.list", {
        "filter": {"iblockId": 11},
        "select": ["id", "name", "code", "iblockSectionId", "active", "UF_*"]
    })
    
    sections = res.get("result", {}).get("sections", [])
    print(f"Выгружено первых разделов: {len(sections)}")
    if sections:
        sample = sections[0]
        print("\nПример структуры раздела:")
        print(json.dumps(sample, indent=2, ensure_ascii=False))

    # 2. Check if UF_COLLECTION and UF_COLLECTION_DESCRIPTION exist in sections
    print("\nПроверяем наличие UF-полей в разделах:")
    uf_keys = set()
    for s in sections:
        for k in s.keys():
            if k.startswith("UF_") or "COLLECTION" in k.upper():
                uf_keys.add(k)
    print("Найденные пользовательские поля разделов:", uf_keys)

if __name__ == "__main__":
    main()
