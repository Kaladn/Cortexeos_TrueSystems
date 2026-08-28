import json
import os
import torch
from torch.nn.utils.rnn import pad_sequence
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset
from peft import get_peft_model, LoraConfig, TaskType
from tqdm import tqdm  # ✅ Progress Bar for Loading & Training

# ✅ Paths
MODEL_PATH = r"A:/Qwen2.5-Math-1.5B"
AI_READY_PATH = r"A:/Compression Engine/ai_ready_data"
SAVE_PATH = r"A:/Compression Engine/Qwen2.5-Trained"

# ✅ Function to Load Pre-Tokenized JSON with Progress
def load_tokenized_file(filepath):
    print(f"🔄 Loading: {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ Loaded {len(data)} entries.")
    return data

# ✅ Function to Format Data with Progress
# ✅ Function to Format Data with Progress
# ✅ Function to Format Data with Debugging
# ✅ Function to Format Data with Debugging
def format_data(dataset):
    formatted_data = []
    print("🔄 Formatting Dataset...")

    # 🔹 Debugging: Print first entry to check structure
    if len(dataset) > 0:
        print("🔍 First Entry Keys:", dataset[0].keys())  # 🔥 This will show available keys

    for entry in tqdm(dataset, desc="📦 Formatting Data", unit="entry"):
        # 🔹 Adjusted to use "input_ids" instead of "token_ids"
        if "input_ids" not in entry or "labels" not in entry:
            print(f"❌ Missing 'input_ids' or 'labels' in entry: {entry}")  # Debugging message
            continue  # Skip malformed entries

        formatted_data.append({
            "input_ids": entry["input_ids"],  # Corrected key name
            "labels": entry["labels"],        # Corrected key name
        })

    print(f"✅ Formatted {len(formatted_data)} entries.")
    return formatted_data

# ✅ Data Collator for Pre-Tokenized Data
def collator(data):
    input_ids = [torch.tensor(f["input_ids"], dtype=torch.long) for f in data]
    labels = [torch.tensor(f["labels"], dtype=torch.long) for f in data]

    input_ids_padded = pad_sequence(input_ids, batch_first=True, padding_value=0)
    labels_padded = pad_sequence(labels, batch_first=True, padding_value=-100)

    return {
        "input_ids": input_ids_padded,
        "labels": labels_padded,
        "attention_mask": (input_ids_padded != 0).long(),
    }

# ✅ Function to Train Model with Training Progress
def train_model(dataset, tokenizer, file_name):
    print(f"🔄 Training on {file_name}...")

    # ✅ Load Model & Apply LoRA
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)

    # ✅ Training Arguments
    training_args = TrainingArguments(
        output_dir=os.path.join(SAVE_PATH, f"checkpoint_{file_name}"),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        save_strategy="epoch",
        save_total_limit=1,
        logging_steps=50,
        evaluation_strategy="no",
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=Dataset.from_list(dataset),
        tokenizer=tokenizer,
        data_collator=collator,
    )

    print(f"🚀 Starting Training on {file_name}...")
    
    with tqdm(total=len(dataset), desc="🎯 Training Progress", unit="batch") as pbar:
        for _ in trainer.get_train_dataloader():
            pbar.update(1)  # ✅ Update progress bar for every batch

    trainer.train()

    print(f"✅ Training Complete for {file_name}!")
    print(f"💾 Model checkpoint saved to: {SAVE_PATH}/checkpoint_{file_name}")

# ✅ Main Execution
if __name__ == "__main__":
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)

    # ✅ Process all JSON files in the directory with Progress Meter
    files = sorted([f for f in os.listdir(AI_READY_PATH) if f.endswith(".json")])
    
    print(f"🔍 Found {len(files)} AI-ready JSON files.")

    for file_name in tqdm(files, desc="🗂 Processing Files", unit="file"):
        file_path = os.path.join(AI_READY_PATH, file_name)
        dataset = load_tokenized_file(file_path)
        dataset = format_data(dataset)

        train_model(dataset, tokenizer, file_name)
