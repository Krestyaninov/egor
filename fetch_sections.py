import os
import json
import urllib.request
import csv

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

def fetch_all_sections(iblock_id=11):
    all_sections = []
    start = 0
    while True:
        res = call_b24("catalog.section.list", {
            "filter": {"iblockId": iblock_id, "active": "Y"},
            "select": ["id", "name", "code", "iblockSectionId", "active", "sort"],
            "start": start
        })
        sections = res.get("result", {}).get("sections", [])
        if not sections:
            break
        all_sections.extend(sections)
        if "next" in res:
            start = res["next"]
        else:
            break
    return all_sections

def main():
    print("=== Выгрузка всех активных разделов каталога (iblockId: 11) ===")
    sections = fetch_all_sections(11)
    print(f"Всего активных разделов: {len(sections)}")
    
    # Построим карту родителей
    sec_map = {s["id"]: s for s in sections}
    for s in sections:
        parent_id = s.get("iblockSectionId")
        if parent_id and parent_id in sec_map:
            s["parent_name"] = sec_map[parent_id]["name"]
        else:
            s["parent_name"] = "--- Корень ---"

    # Сохраняем в CSV
    with open("active_catalog_sections.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "code", "iblockSectionId", "parent_name", "sort"])
        writer.writeheader()
        for s in sections:
            writer.writerow({
                "id": s.get("id"),
                "name": s.get("name"),
                "code": s.get("code"),
                "iblockSectionId": s.get("iblockSectionId"),
                "parent_name": s.get("parent_name"),
                "sort": s.get("sort")
            })
    print("Сохранено в active_catalog_sections.csv")

    # Выведем корневые разделы и основные ветки
    root_sections = [s for s in sections if not s.get("iblockSectionId")]
    print(f"\nКорневых разделов: {len(root_sections)}")
    for r in root_sections[:20]:
        children = [s for s in sections if s.get("iblockSectionId") == r["id"]]
        print(f"- [{r['id']}] {r['name']} (подразделов: {len(children)})")

if __name__ == "__main__":
    main()
