import json
import random

def assign_font_symbols(json_path):
    """Adds missing font symbols to the Symbolis dictionary."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for word, details in data.items():
        if "font_symbol" not in details:
            details["font_symbol"] = chr(random.randint(0x2800, 0x28FF))  # Use Braille Unicode

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Updated: {json_path}")

# Run on all symbol JSON files
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    assign_font_symbols(f"A:/Symbolis_TXT_Conversion/json_dictionary/Symbols_{letter}.json")
