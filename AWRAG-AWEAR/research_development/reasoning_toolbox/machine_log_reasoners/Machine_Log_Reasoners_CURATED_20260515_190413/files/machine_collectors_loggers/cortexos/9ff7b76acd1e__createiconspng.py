import os
import json
from PIL import Image, ImageDraw

# Directories
input_json = r"A:\Compression Engine\tokenized_dictionary\Symbols_X.json"
output_directory = r"A:\Compression Engine\font_symbols"
os.makedirs(output_directory, exist_ok=True)

# Grid settings
GRID_SIZE = 16  # Static grid (fits 256-bit words)
DOT_SIZE = 2  # Dot size (can be adjusted for visibility)
IMG_SIZE = GRID_SIZE * DOT_SIZE  # Image size (square)

def binary_to_grid(binary_str):
    """Converts binary string to a 2D grid representation."""
    grid = []
    row = []
    for bit in binary_str:
        row.append(1 if bit == "1" else 0)
        if len(row) == GRID_SIZE:
            grid.append(row)
            row = []
    if row:
        grid.append(row + [0] * (GRID_SIZE - len(row)))  # Pad last row
    return grid

def create_font_symbol(binary_str, word):
    """Generates a pictorial font symbol based on binary representation."""
    grid = binary_to_grid(binary_str)
    
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), "white")
    draw = ImageDraw.Draw(img)

    for y, row in enumerate(grid):
        for x, bit in enumerate(row):
            if bit:
                draw.rectangle(
                    [(x * DOT_SIZE, y * DOT_SIZE), ((x + 1) * DOT_SIZE, (y + 1) * DOT_SIZE)],
                    fill="black"
                )

    file_path = os.path.join(output_directory, f"{word}.png")
    img.save(file_path)
    return file_path

# Load dictionary & generate symbols
with open(input_json, "r", encoding="utf-8") as f:
    dictionary = json.load(f)

for word, details in dictionary.items():
    if "binary" in details and details["binary"]:
        font_symbol_path = create_font_symbol(details["binary"], word)
        details["font_symbol"] = font_symbol_path  # Store path in JSON

# Save updated JSON
output_json = os.path.join(output_directory, "updated_symbols.json")
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(dictionary, f, indent=4, ensure_ascii=False)

print("✅ All word symbols generated & saved!")
