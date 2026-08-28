import json
import nltk
from nltk.tokenize import word_tokenize
from nltk import pos_tag

# Download necessary NLTK components
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

# Paths (update these to match your actual file locations)
SLOT_FILE = "/home/lee/Desktop/Lexicon_Data/slots.json"  # Input slots file
VERIFIED_WORDS_FILE = "/home/lee/Desktop/Lexicon_Data/verified_words.json"  # Verified words

OUTPUT_FILE = "/home/lee/Desktop/Lexicon_Data/filled_lexicon.json"  # Output file

# Load verified words (structured as a dictionary)
with open(VERIFIED_WORDS_FILE, 'r', encoding='utf-8') as f:
    verified_words = json.load(f)

# Load empty slots structure
with open(SLOT_FILE, 'r', encoding='utf-8') as f:
    slots = json.load(f)

# Function to process words
def process_word(word):
    """ Tokenize and categorize a word """
    tokens = word_tokenize(word)
    pos_tags = pos_tag(tokens)
    return {
        "tokenized": tokens,
        "part_of_speech": [tag for _, tag in pos_tags]
    }

# Fill available slots with verified words
for i, slot in enumerate(slots):
    if slot["status"] == "AVAILABLE" and i < len(verified_words):
        word = list(verified_words.keys())[i]
        metadata = process_word(word)

        slot.update({
            "word": word,
            "tokenized": metadata["tokenized"],
            "part_of_speech": metadata["part_of_speech"],
            "status": "FILLED"
        })

# Save the updated lexicon
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(slots, f, indent=4)

print(f"Lexicon successfully updated! Saved to: {OUTPUT_FILE}")
