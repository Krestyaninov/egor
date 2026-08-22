import glob
import json
import os

files = glob.glob("/Users/mk/.gemini/antigravity/brain/fc651b16-767b-45cd-88c7-8271826195db/.system_generated/logs/*.jsonl")
for fn in files:
    with open(fn, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                c = data.get("content", "")
                if "Дата создания заказа" in c:
                    csv_part = c[c.find("Дата создания заказа"):]
                    print(f"Found in {fn}, length: {len(csv_part.splitlines())}")
                    with open("sales_margin_full.csv", "w", encoding="utf-8") as out:
                        out.write(csv_part.strip())
            except:
                pass
