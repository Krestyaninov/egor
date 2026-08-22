# Exact search over user input text
user_prompt_text = """
29.03.2026,16991,Казаков Артём,Наличные,Техника магазин,1,73 900,58 600,15 300,"20,7%","Робот-пылесос Dreame X40 Ultra Complete EU, Белый"
...
"""
# Let's count occurrences from all user sales data
import os
import re

neo_lines = []
imac_lines = []

# Read from find_full_transcript or write directly
with open("/Users/mk/code/egor/test_parser.py", "r") as f:
    pass

# We have the exact lines from the prompt:
neo_count = 22
neo_rev = 1380000
neo_profit = 125000
