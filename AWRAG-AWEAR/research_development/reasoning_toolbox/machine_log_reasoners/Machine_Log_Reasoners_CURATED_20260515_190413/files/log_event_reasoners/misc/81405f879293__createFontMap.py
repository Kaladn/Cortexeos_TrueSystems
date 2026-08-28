import json
import os

def generate_dot_matrix(symbol):
    """Creates an 8x8 dot-matrix pattern for a given symbol (placeholder function)."""
    return [[1 if (i+j) % 2 == 0 else 0 for j in range(8)] for i in range(8)]

def assign_symbols_to_fonts():
    """Loads symbols and assigns dot-matrix font patterns."""
    symbols_data = json.load(open("A:/Symbolis/data/json/symbols.json", "r"))
    
    font_map = {}
    for key, symbols in symbols_data.items():
        font_map[key] = {symbol: generate_dot_matrix(symbol) for symbol in symbols[:100]}  # Example: first 100

    os.makedirs("A:/Symbolis/data/json/", exist_ok=True)
    with open("A:/Symbolis/data/json/font_map.json", 'w', encoding='utf-8') as f:
        json.dump(font_map, f, indent=4)

    print("✅ Dot-matrix font mappings saved to JSON.")

if __name__ == "__main__":
    assign_symbols_to_fonts()
