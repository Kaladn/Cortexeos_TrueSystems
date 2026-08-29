import json

json_path = "A:/Symbolis_TXT_Conversion/json_dictionary/Symbols_A.json"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for word, details in data.items():
    if "binary" not in details:
        print(f"❌ Missing 'binary' for: {word}")
