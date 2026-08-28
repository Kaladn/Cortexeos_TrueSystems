import json
import random

# ✅ 8x8 Dot Matrix Generator
def generate_dot_matrix():
    """Creates a unique 8x8 dot matrix representation."""
    return [[random.choice([0, 1]) for _ in range(8)] for _ in range(8)]

# ✅ Convert Binary Matrix to Hex
def matrix_to_hex(matrix):
    """Converts an 8x8 matrix to a hex string."""
    binary_str = ''.join(str(bit) for row in matrix for bit in row)
    hex_str = hex(int(binary_str, 2))[2:].upper()
    return f"0x{hex_str.zfill(16)}"

# ✅ Patch Missing Binary & Hex Fields
def patch_json(json_path):
    """Adds missing binary and hex encodings to JSON files."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = False
    for word, details in data.items():
        if "binary" not in details or "hex" not in details:
            dot_matrix = generate_dot_matrix()
            details["binary"] = dot_matrix
            details["hex"] = matrix_to_hex(dot_matrix)
            details["font_symbol"] = None  # Placeholder until fonts are mapped
            updated = True
    
    if updated:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Patched: {json_path}")

# ✅ Run Fix on All JSON Symbol Files
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    patch_json(f"A:/Symbolis_TXT_Conversion/json_dictionary/Symbols_{letter}.json")

print("🔥 All missing 'binary' and 'hex' fields have been generated!")  
 --- before curtrent fix json