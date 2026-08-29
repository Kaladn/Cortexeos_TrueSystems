import json
import hashlib
import tiktoken
from tqdm import tqdm
from collections import Counter
import matplotlib.pyplot as plt

# Load words
with open("expanded_lexicon.json", "r", encoding="utf-8") as f:
    words = json.load(f)

tokenizer = tiktoken.get_encoding("cl100k_base")

def generate_binary_hexi(word):
    hash_object = hashlib.sha256(word.encode("utf-8"))
    binary = bin(int(hash_object.hexdigest(), 16))[2:].zfill(256)
    hexi = hex(int(binary, 2))[2:].zfill(64)
    return binary, hexi

neurons = []
starting_letters = Counter()

print("🧠 Building neurons...\n")

for word in tqdm(words, desc="Forging Neurons"):
    word = word.strip().lower()
    binary, hexi = generate_binary_hexi(word)
    
    try:
        token_ids = tokenizer.encode(word)
        gpt_token = {
            "id": token_ids[0] if token_ids else None,
            "text": word
        }
    except Exception:
        gpt_token = {"id": None, "text": word}

    neuron = {
        "word": word,
        "binary": binary,
        "hexi": hexi,
        "font_symbol": "pending",
        "tone": None,
        "gpt_token": gpt_token
    }

    neurons.append(neuron)
    if word:  # safety check
        starting_letters[word[0]] += 1

# Save results
with open("neuron_staging.json", "w", encoding="utf-8") as f:
    json.dump(neurons, f, indent=2)

print(f"\n✅ Total neurons built: {len(neurons)}")
print("📊 Generating quick insights...")

# Simple graph: top 10 starting letters
top_letters = starting_letters.most_common(10)
letters, counts = zip(*top_letters)

plt.figure(figsize=(10, 6))
plt.bar(letters, counts)
plt.title("Top 10 Starting Letters in Lexicon")
plt.xlabel("Letter")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig("lexicon_letter_distribution.png")
plt.show()

print("📈 Chart saved as 'lexicon_letter_distribution.png'")
