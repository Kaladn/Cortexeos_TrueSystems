import os
import re
import json
from tqdm import tqdm

# === CONFIGURATION ===
SYMBOL_PREFIX = "SYM"
REMOVE_EMOJIS = True
KEEP_PUNCTUATION = False

# === FUNCTIONS ===
def tokenize_text(text, word2symbol, symbol_counter, word_freq):
    if REMOVE_EMOJIS:
        text = text.encode('ascii', errors='ignore').decode()  # Safer emoji removal

    if KEEP_PUNCTUATION:
        words = re.findall(r'\b\w+[\w\.\,\:\;\'\"\!\?\-]*\b', text.lower())
    else:
        words = re.findall(r'\b\w+\b', text.lower())

    symbolized = []
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
        if word not in word2symbol:
            word2symbol[word] = f"{SYMBOL_PREFIX}{symbol_counter}"
            symbol_counter += 1
        symbolized.append(word2symbol[word])

    return symbolized, symbol_counter


def process_txt_files_in_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "tokenized")
    os.makedirs(output_dir, exist_ok=True)

    word2symbol = {}
    word_freq = {}
    symbol_counter = 1
    txt_files = [f for f in os.listdir(current_dir) if f.endswith(".txt")]

    print(f"\n📁 Found {len(txt_files)} .txt files. Processing with tokenizer...\n")

    for file in tqdm(txt_files, desc="Tokenizing Files", unit="file"):
        input_path = os.path.join(current_dir, file)
        output_path = os.path.join(output_dir, f"tokenized_{file}")

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except Exception as e:
            print(f"⚠️ Skipped {file} due to error: {e}")
            continue

        symbolized, symbol_counter = tokenize_text(raw_text, word2symbol, symbol_counter, word_freq)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(' '.join(symbolized))

    # Flip the mapping for correct token key → word value
    symbol2word = {v: k for k, v in word2symbol.items()}

    # Save correct mapping as primary dictionary
    token_map_path = os.path.join(output_dir, "symbol2word.json")
    reverse_map_path = os.path.join(output_dir, "word2symbol.json")
    frequency_path = os.path.join(output_dir, "word_frequency.json")

    with open(token_map_path, 'w', encoding='utf-8') as f:
        json.dump(symbol2word, f, indent=2)

    with open(reverse_map_path, 'w', encoding='utf-8') as f:
        json.dump(word2symbol, f, indent=2)

    with open(frequency_path, 'w', encoding='utf-8') as f:
        json.dump(word_freq, f, indent=2)

    print(f"\n✅ All files processed and saved to: {output_dir}")
    print(f"🔣 Primary token map (SYM -> word): {token_map_path}")
    print(f"↩️  Reverse token map (word -> SYM): {reverse_map_path}")
    print(f"📊 Word frequency saved as: {frequency_path}")
    print(f"🔢 Total unique tokens: {len(symbol2word)}\n")


if __name__ == '__main__':
    process_txt_files_in_dir()
