import json
import os

# 🔹 Set dictionary file path
dictionary_path = "C:/Users/mydyi/OneDrive/Documents/Desktop/DATA BACKUP/dictionary.json"

# 🔹 Verify dictionary file exists
if not os.path.exists(dictionary_path):
    print("❌ ERROR: Dictionary file not found! Please generate it first.")
    exit(1)

# 🔹 Load dictionary
try:
    with open(dictionary_path, "r", encoding="utf-8") as f:
        dictionary = json.load(f)
    print("✅ Dictionary loaded successfully! Type a word to look up.")
except Exception as e:
    print(f"❌ ERROR: Failed to load dictionary. Details: {e}")
    exit(1)

def get_symbol(word):
    """Retrieve the symbol for a given word (case-insensitive)."""
    word_lower = word.lower()
    symbol = dictionary.get(word_lower)

    if symbol:
        return symbol
    else:
        with open("missing_words.log", "a", encoding="utf-8") as log_file:
            log_file.write(word + "\n")  # Logs missing words for future updates
        return "❌ Word not found (Logged for review)"

# 🔹 Interactive Lookup Loop
if __name__ == "__main__":
    while True:
        word = input("\n🔎 Enter a word to look up (or type 'exit' to quit): ").strip()

        if word.lower() == "exit":
            print("👋 Exiting lookup. See you next time!")
            break

        symbol = get_symbol(word)
        print(f"🟢 Symbol for '{word}': {symbol}")


