import json

with open("A:/Symbolis_TXT_Conversion/json_dictionary/Symbols_A.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for word, details in data.items():
    if "font_symbol" not in details:
        print(f"❌ Missing 'font_symbol' for: {word}")
