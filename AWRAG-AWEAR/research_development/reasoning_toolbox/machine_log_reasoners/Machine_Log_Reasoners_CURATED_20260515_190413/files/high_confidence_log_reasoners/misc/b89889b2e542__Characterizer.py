import os
import json
import re
from time import time
from tqdm import tqdm  # 🔥 LIVE Progress Bars

# Paths
DICTIONARY_FOLDER = r"C:\Users\mydyi\Desktop\words with character font label"
OUTPUT_FOLDER = r"C:\Users\mydyi\Desktop\symbol_output"

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def sanitize_filename(word, max_length=100):
    """🔥 Shortens and sanitizes filenames to prevent path errors"""
    safe_word = re.sub(r'[^a-zA-Z0-9_-]', '_', word)  # Replace special characters
    return safe_word[:max_length]  # Trim length to max 100 chars

def load_full_dictionary():
    """🔥 Load ALL dictionary files into RAM with PROGRESS BAR"""
    full_dict = {}
    dictionary_files = sorted([os.path.join(DICTIONARY_FOLDER, f) for f in os.listdir(DICTIONARY_FOLDER) if f.endswith(".json")])

    print(f"📂 Loading {len(dictionary_files)} dictionary files into RAM...")
    start_time = time()

    for file in tqdm(dictionary_files, desc="🔄 Loading Files", unit="file"):
        with open(file, "r", encoding="utf-8") as f:
            full_dict.update(json.load(f))  # Merge dictionaries

    print(f"✅ Loaded {len(full_dict):,} symbols into RAM in {time() - start_time:.2f} sec")
    return full_dict

def generate_svg(symbol_data):
    """🔥 Generate an SVG for a single word symbol"""
    word, data = symbol_data
    binary_code = data["binary"]

    svg_content = [
        '<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">',
        '<rect width="100" height="100" fill="white"/>'
    ]

    # Convert binary representation to grid pattern
    grid_size = 10
    for i, bit in enumerate(binary_code):
        if bit == "1":
            x = (i % grid_size) * 10
            y = (i // grid_size) * 10
            svg_content.append(f'<rect x="{x}" y="{y}" width="10" height="10" fill="black"/>')

    svg_content.append("</svg>")
    return sanitize_filename(word), "\n".join(svg_content)

def process_symbols(dictionary):
    """🔥 Generate ALL SVGs with a PROGRESS BAR"""
    print(f"🖌 Generating {len(dictionary):,} SVG symbols using a SINGLE THREAD...")
    start_time = time()

    all_svgs = []
    for symbol in tqdm(dictionary.items(), desc="🎨 Creating Symbols", unit="symbol"):
        all_svgs.append(generate_svg(symbol))  # Process one by one (Single Thread)

    print(f"✅ Generated all SVGs in {time() - start_time:.2f} sec. Now saving...")
    save_all_svgs(all_svgs)

def save_all_svgs(all_svgs):
    """🔥 Save ALL SVGs with a PROGRESS BAR"""
    start_time = time()

    for word, svg in tqdm(all_svgs, desc="💾 Saving Files", unit="file"):
        output_file = os.path.join(OUTPUT_FOLDER, f"{word}.svg")
        try:
            with open(output_file, "w", encoding="utf-8") as svg_file:
                svg_file.write(svg)
        except Exception as e:
            print(f"❌ Failed to save {word}.svg: {e}")

    print(f"✅ Saved {len(all_svgs):,} SVGs in {time() - start_time:.2f} sec")

if __name__ == "__main__":
    full_dict = load_full_dictionary()
    process_symbols(full_dict)
    print("🎉 All SVG symbols generated successfully!")
