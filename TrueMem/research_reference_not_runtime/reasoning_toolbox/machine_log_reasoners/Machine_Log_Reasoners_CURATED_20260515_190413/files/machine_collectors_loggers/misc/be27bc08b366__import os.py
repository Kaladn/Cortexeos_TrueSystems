import os
import sys
import json
import string
from symbolis_builder import assign_symbol
from symbolis_encoder import encode_text
from symbolis_decoder import decode_text
from symbolis_tmx import generate_tmx
from validation import validate_dictionary

# Set base directory for storing dictionary outputs
BASE_DIR = r"A:\Compression Engine\dictionary"

# Ensure alphabetized folders exist
def ensure_folders():
    for letter in string.ascii_uppercase:
        folder_path = os.path.join(BASE_DIR, letter)
        os.makedirs(folder_path, exist_ok=True)

def save_to_alphabetized_folder(word, symbol):
    """Saves the word-symbol pair into the respective folder based on the first letter."""
    first_letter = word[0].upper()
    folder_path = os.path.join(BASE_DIR, first_letter)
    file_path = os.path.join(folder_path, f"{first_letter}_dictionary.json")
    
    # Load existing data
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}
    
    # Update with new symbol
    data[word] = symbol
    
    # Save back to JSON
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def menu():
    """Displays the main menu."""
    print("\n🔥 SYMBOLIS: MACHINE-NATIVE LANGUAGE 🔥")
    print("1️⃣ Assign a Symbol to a Word")
    print("2️⃣ Encode Text to Symbolis")
    print("3️⃣ Decode Symbolis to English")
    print("4️⃣ Generate TMX File")
    print("5️⃣ Validate Dictionary")
    print("0️⃣ Exit")
    
    choice = input("\nSelect an option: ")
    return choice.strip()

def main():
    """Main execution loop for Symbolis."""
    ensure_folders()
    while True:
        choice = menu()
        
        if choice == "1":
            word = input("Enter word to assign a symbol: ").strip()
            symbol = assign_symbol(word)
            save_to_alphabetized_folder(word, symbol)
            print(f"✅ Assigned and Saved: {word} → {symbol}")
        
        elif choice == "2":
            text = input("Enter text to encode: ").strip()
            encoded_text = encode_text(text)
            print(f"🔥 Encoded Text: {encoded_text}")
        
        elif choice == "3":
            symbols = input("Enter Symbolis text to decode: ").strip()
            decoded_text = decode_text(symbols)
            print(f"🔓 Decoded Text: {decoded_text}")
        
        elif choice == "4":
            result = generate_tmx()
            print(result)
        
        elif choice == "5":
            validation_result = validate_dictionary()
            print(validation_result)
        
        elif choice == "0":
            print("🚀 Exiting Symbolis. See you soon!")
            sys.exit()
        
        else:
            print("⚠️ Invalid option! Please try again.")

if __name__ == "__main__":
    main()
