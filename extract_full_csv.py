import json
import re

# Let's inspect transcript to get the exact raw text of the user input!
transcript_path = "/Users/mk/.gemini/antigravity/brain/fc651b16-767b-45cd-88c7-8271826195db/.system_generated/logs/transcript_full.jsonl"
with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data.get("type") == "USER_INPUT" and "Дата создания заказа" in data.get("content", ""):
            user_text = data["content"]
            # extract csv from user_text
            csv_part = user_text[user_text.find("Дата создания заказа"):]
            with open("sales_margin_full.csv", "w", encoding="utf-8") as out:
                out.write(csv_part.strip())
            print(f"Successfully extracted full CSV! Lines: {len(csv_part.splitlines())}")
            break
