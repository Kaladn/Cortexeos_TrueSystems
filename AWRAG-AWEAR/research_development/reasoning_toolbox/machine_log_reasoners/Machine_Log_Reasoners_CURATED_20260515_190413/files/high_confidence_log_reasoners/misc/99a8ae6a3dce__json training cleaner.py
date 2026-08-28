import json
import re
import random
import os
import sys
from collections import defaultdict
from pathlib import Path

# ─────────────────────────────────────────────────────────────
#                💀 Cortex Profane Filter v1.0 💀
#       A symbolic shield for cleaning up that dirty data.
# ─────────────────────────────────────────────────────────────

print("""
╔════════════════════════════════════════════════════════╗
║            💀  Cortex Profane Filter v1.0  💀          ║
║         Symbolic cleanup for unruly training data      ║
╚════════════════════════════════════════════════════════╝
""")

# Get the directory where the script lives
SCRIPT_DIR = Path(__file__).parent.resolve()
THESAURUS_PATH = SCRIPT_DIR / "profanity_thesaurus.json"

# Load the profanity thesaurus
try:
    with open(THESAURUS_PATH, "r", encoding="utf-8") as f:
        profanity_dict = json.load(f)
    print(f"📖 Loaded {len(profanity_dict)} profane terms from thesaurus.\n")
except Exception as e:
    print(f"❌ Failed to load profanity thesaurus: {e}")
    sys.exit(1)

# Create regex pattern for fast replacement
profanity_pattern = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in profanity_dict.keys()) + r")\b",
    flags=re.IGNORECASE
)

# Track how many times each profane word was replaced
profanity_tally = defaultdict(int)

def replace_profanity(text):
    def replacement(match):
        word = match.group(0).lower()
        replacements = profanity_dict.get(word)
        if replacements:
            profanity_tally[word] += 1
            return random.choice(replacements)
        return word  # fallback
    return profanity_pattern.sub(replacement, text)

def process_jsonl(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"❌ Error: '{input_path}' does not exist.")
        return

    with open(input_path, "r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:

        for line in infile:
            try:
                item = json.loads(line)
                if 'completion' in item:
                    item['completion'] = replace_profanity(item['completion'])
                outfile.write(json.dumps(item, ensure_ascii=False) + "\n")
            except json.JSONDecodeError:
                continue

    # Print results
    total = sum(profanity_tally.values())
    print("\n🔍 Profanity Replacement Summary:")
    for word, count in sorted(profanity_tally.items(), key=lambda x: -x[1]):
        print(f"  {word:15s} → {count} replacements")

    print(f"\n🧼 Total Profanities Replaced: {total}")
    print(f"✅ Output saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        input_file = input("📂 Enter path to your input .jsonl file: ").strip()

    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_cleaned{ext or '.jsonl'}"

    print(f"\n⚙️ Processing file: {input_file}")
    process_jsonl(input_file, output_file)
