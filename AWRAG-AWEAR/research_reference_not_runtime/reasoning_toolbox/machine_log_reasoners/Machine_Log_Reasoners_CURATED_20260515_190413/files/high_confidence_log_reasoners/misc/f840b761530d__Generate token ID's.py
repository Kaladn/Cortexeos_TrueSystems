import os
import json
import numpy as np
from tqdm import tqdm
from transformers import AutoTokenizer

# === CONFIGURATION ===
MODEL_NAME = "Qwen/Qwen1.5-0.5B"
INPUT_FILE = r"E:\split_conversations\pretrain_ready.txt"
OUTPUT_JSONL = "token_ids.jsonl"
OUTPUT_IDS_NPY = "token_ids.npy"
OUTPUT_MASKS_NPY = "attention_masks.npy"
MAX_LENGTH = 512

# === LOAD TOKENIZER ===
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

input_ids_all = []
attention_masks_all = []

with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
     open(OUTPUT_JSONL, 'w', encoding='utf-8') as f_out:

    lines = f_in.readlines()
    print(f"\n🧠 Tokenizing {len(lines)} lines from: {INPUT_FILE}\n")

    for line in tqdm(lines, desc="Tokenizing", unit="line"):
        line = line.strip()
        if not line:
            continue

        encoded = tokenizer(
            line,
            padding='max_length',
            truncation=True,
            max_length=MAX_LENGTH,
            return_attention_mask=True,
            return_tensors='np'
        )

        input_ids = encoded['input_ids'][0].tolist()
        attention_mask = encoded['attention_mask'][0].tolist()

        json_line = json.dumps({
            "input_ids": input_ids,
            "attention_mask": attention_mask
        })
        f_out.write(json_line + '\n')

        input_ids_all.append(input_ids)
        attention_masks_all.append(attention_mask)

# === SAVE AS NP ARRAYS ===
np.save(OUTPUT_IDS_NPY, np.array(input_ids_all, dtype=np.int32))
np.save(OUTPUT_MASKS_NPY, np.array(attention_masks_all, dtype=np.int32))

print("\n✅ Tokenization complete.")
print(f"📄 JSONL file: {OUTPUT_JSONL}")
print(f"📦 Numpy arrays: {OUTPUT_IDS_NPY}, {OUTPUT_MASKS_NPY}\n")
