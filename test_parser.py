import csv
import io
import re

# Read data from the python script containing user raw text
# Let's parse all lines directly
with open("create_full_csv.py", "r", encoding="utf-8") as f:
    text = f.read()

# Extract content inside triple quotes
match = re.search(r'content = """(.*?)"""', text, re.DOTALL)
if match:
    raw_csv = match.group(1).strip()
else:
    raw_csv = ""

print(f"Total characters in CSV: {len(raw_csv)}")
reader = csv.DictReader(io.StringIO(raw_csv))
rows = list(reader)
print(f"Total rows parsed: {len(rows)}")
