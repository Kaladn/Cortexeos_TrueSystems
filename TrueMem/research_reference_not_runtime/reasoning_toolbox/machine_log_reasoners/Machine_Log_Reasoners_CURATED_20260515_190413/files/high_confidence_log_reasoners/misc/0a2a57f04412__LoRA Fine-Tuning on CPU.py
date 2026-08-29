import os
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import Dataset
from peft import get_peft_model, LoraConfig, TaskType
from tqdm import tqdm  # ✅ Process Meter for Progress Tracking

# ✅ Paths
MODEL_PATH = r"A:/Qwen2.5-Math-1.5B"
DATA_PATH = r"A:/Compression Engine/merged_dictionary.json"
SAVE_PATH = r"A:/Compression Engine/Qwen2.5-Trained"

# ✅ Load Merged Dictionary Dataset with Progress Bar
print("🔄 Loading dataset...")
with open(DATA_PATH, "r", encoding="utf-8") as f:
    training_data = json.load(f)

print(f"✅ Loaded {len(training_data)} entries from dictionary.")

# ✅ Convert JSON to Hugging Face Dataset
dataset = Dataset.from_list(training_data)

# ✅ Load Model & Tokenizer (Local Only)
print("🔄 Loading Model & Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True)
print("✅ Model & Tokenizer loaded!")

# ✅ LoRA Config for CPU Training
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
)

model = get_peft_model(model, lora_config)

# ✅ Training Parameters
training_args = TrainingArguments(
    output_dir=SAVE_PATH,
    per_device_train_batch_size=1,  # ✅ Keep it low for CPU
    num_train_epochs=3,  # ✅ Adjust as needed
    save_strategy="epoch",
    save_total_limit=1,
    logging_dir=f"{SAVE_PATH}/logs",
    report_to="none",
    no_cuda=True,  # ✅ Runs on CPU
)

# ✅ Progress Meter for Dataset Processing
print("🔄 Tokenizing dataset...")
progress_bar = tqdm(total=len(training_data), desc="Tokenizing", unit="entry")

tokenized_data = []
for entry in training_data:
    input_ids = tokenizer(entry["input"], truncation=True, padding="max_length", max_length=256, return_tensors="pt")["input_ids"].tolist()
    output_ids = tokenizer(entry["output"], truncation=True, padding="max_length", max_length=256, return_tensors="pt")["input_ids"].tolist()
    tokenized_data.append({"input_ids": input_ids, "output_ids": output_ids})
    progress_bar.update(1)

progress_bar.close()
print("✅ Tokenization Complete!")

# ✅ Convert Tokenized Data to Dataset
dataset = Dataset.from_list(tokenized_data)

# ✅ Trainer Setup with Progress Logging
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    tokenizer=tokenizer,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

# ✅ Training Progress Bar
print("🚀 Starting Training...")
trainer.train()
print("✅ Training Complete!")

# ✅ Save Fine-Tuned Model
print("💾 Saving Model...")
model.save_pretrained(SAVE_PATH)
tokenizer.save_pretrained(SAVE_PATH)

print(f"✅ Model Saved at {SAVE_PATH} 🎉")
