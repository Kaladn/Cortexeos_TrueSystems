import os
import re

# ==== CONFIG ====
input_dir = r"C:\Users\Blame\Desktop\combined_texts"
output_dir = os.path.join(input_dir, "symbolized")
os.makedirs(output_dir, exist_ok=True)

# Load your bin mappings (assuming they're simple text files with one mapping per line for now)
def load_symbol_bin(file_path):
    mapping = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                word, symbol = line.strip().split(",")
                mapping[word.lower()] = symbol
    return mapping

# Combine all bins
symbol_bins = {}
symbol_bins.update(load_symbol_bin(r"C:\path\to\symbols_1byte.bin"))
symbol_bins.update(load_symbol_bin(r"C:\path\to\symbols_2byte.bin"))
symbol_bins.update(load_symbol_bin(r"C:\path\to\symbols_3byte.bin"))
symbol_bins.update(load_symbol_bin(r"C:\path\to\symbols_4byte.bin"))

# Regex to split text into words + punctuation
token_pattern = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# Process each file
for filename in os.listdir(input_dir):
    if filename.endswith(".txt"):
        input_path = os.path.join(input_dir, filename)
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        tokens = token_pattern.findall(text)
        symbolized_tokens = []

        for token in tokens:
            token_lower = token.lower()
            if token_lower in symbol_bins:
                symbolized_tokens.append(symbol_bins[token_lower])
            elif re.match(r"[^\w\s]", token):  # punctuation
                symbolized_tokens.append(token)
            else:
                symbolized_tokens.append(token)  # fallback (or could skip)

        # Join without any whitespace
        final_text = "".join(symbolized_tokens)

        output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_symbolized_noWS.txt")
        with open(output_path, "w", encoding="utf-8") as f_out:
            f_out.write(final_text)

        print(f"✅ Processed: {filename} → {os.path.basename(output_path)}")

print("🚀 All files processed and symbolized. No whitespace left standing.")
