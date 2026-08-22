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
    print("=== 1. Проверяем все направления (категории) сделок ===")
    categories = call_b24("crm.dealcategory.list")
    print("crm.dealcategory.list:", json.dumps(categories, indent=2, ensure_ascii=False))

    cat_list = categories.get("result", [])
    all_stages = {}
    
    # Category 0 (General)
    cat_ids = [0] + [c["ID"] for c in cat_list]
    for cid in cat_ids:
        stages = call_b24("crm.dealcategory.stage.list", {"id": cid})
        print(f"\n--- Стадии для Категории {cid} ---")
        for s in stages.get("result", []):
            st_id = s.get("STATUS_ID")
            st_name = s.get("NAME")
            sem = s.get("SEMANTICS") # P - process, S - success, F - fail
            all_stages[st_id] = {
                "name": st_name,
                "semantics": sem,
                "category_id": cid,
                "sort": s.get("SORT")
            }
            print(f"  [{sem or ' '}] ID: {st_id:20s} | Sort: {s.get('SORT'):4} | Name: {st_name}")

    # Также проверим crm.status.list для DEAL_STAGE
    res_status = call_b24("crm.status.list", {"filter": {"%ENTITY_ID": "STAGE"}})
    print(f"\nВсего записей в crm.status.list: {len(res_status.get('result', []))}")
    for st in res_status.get("result", []):
        st_id = st.get("STATUS_ID")
        if st_id not in all_stages:
            sem = st.get("SEMANTICS")
            all_stages[st_id] = {
                "name": st.get("NAME"),
                "semantics": sem,
                "category_id": "status_list"
            }
            print(f"  [STATUS_LIST] [{sem or ' '}] ID: {st_id:20s} | Name: {st.get('NAME')}")

    # Сохраним полный маппинг стадий в JSON
    with open("all_deal_stages.json", "w", encoding="utf-8") as f:
        json.dump(all_stages, f, indent=2, ensure_ascii=False)
    print("\nСохранено в all_deal_stages.json!")

if __name__ == "__main__":
    main()
