import json

with open("all_deal_stages.json", "r", encoding="utf-8") as f:
    stages = json.load(f)

print(f"Всего стадий в базе: {len(stages)}")
for k, v in stages.items():
    if v.get("category_id") in [0, "0", 1, 2, 3, 4, 5]:
        print(f"Cat {v.get('category_id')}: [{v.get('semantics') or 'P'}] {k:25s} -> {v.get('name')}")
