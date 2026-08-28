import json
import os
import torch
from torch.nn.utils.rnn import pad_sequence
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset
from peft import get_peft_model, LoraConfig, TaskType

# ✅ Paths
MODEL_PATH = r"A:/Qwen2.5-Math-1.5B"
TOKENIZED_DICT_PATH = r"A:/Compression Engine/tokenized_dictionary"
SAVE_PATH = r"A:/Compression Engine/Qwen2.5-Trained"

# ✅ Function to Select File
def select_file(directory=TOKENIZED_DICT_PATH):
    files = [f for f in os.listdir(directory) if f.endswith(".json")]
    if not files:
        raise ValueError(f"No JSON files found in {directory}")
    for idx, file in enumerate(files, 1):
        print(f"{idx}. {file}")
    choice = int(input("\n🔍 Select a file number to load: ")) - 1
    return os.path.join(directory, files[choice])

# ✅ Function to Load Pre-Tokenized JSON
def load_tokenized_file(filepath):
    print(f"🔄 Loading: {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ Function to Format Data
def format_data(example):
    return {
        "input_ids": example["token_ids"],  # ✅ Use `token_ids`
        "labels": example["token_ids"],     # ✅ Use `token_ids` for labels
    }

# ✅ Data Collator for Pre-Tokenized Data
def collator(data):
    input_ids = [torch.tensor(f["input_ids"], dtype=torch.long) for f in data]
    labels = [torch.tensor(f["labels"], dtype=torch.long) for f in data]

    input_ids_padded = pad_sequence(input_ids, batch_first=True, padding_value=0)
    labels_padded = pad_sequence(labels, batch_first=True, padding_value=-100)  # ✅ Use `-100`

    return {
        "input_ids": input_ids_padded,
        "labels": labels_padded,
        "attention_mask": (input_ids_padded != 0).long(),
    }

# ✅ Function to Train Model
def train_model(dataset, tokenizer, eval_dataset=None):
    print("🔄 Loading Model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        local_files_only=True
    )
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
        output_dir=SAVE_PATH,
        per_device_train_batch_size=4,  # ✅ Faster training
        gradient_accumulation_steps=4,  # ✅ Simulates batch size of 16
        num_train_epochs=3,
        save_strategy="epoch",
        save_steps=500,
        logging_steps=50,
        eval_strategy="epoch" if eval_dataset else "no",  # ✅ Fixed deprecated `evaluation_strategy`
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=Dataset.from_list(dataset),
        eval_dataset=Dataset.from_list(eval_dataset) if eval_dataset else None,
        data_collator=collator,
        processing_class=tokenizer,  # ✅ Fixed deprecated `tokenizer`
    )

    print("🚀 Starting Training...")
    trainer.train()
    print("✅ Training Complete!")
    print(f"💾 Model saved to: {SAVE_PATH}")

# ✅ Main Execution
if __name__ == "__main__":
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)

    # Load training data
    train_file = select_file()
    dataset = load_tokenized_file(train_file)
    dataset = [format_data(entry) for entry in dataset.values()]  # ✅ Fixed

    # Optionally load evaluation data
    eval_dataset = None
    if input("\n📊 Load an evaluation dataset? (y/n): ").lower() == "y":
        eval_file = select_file()
        eval_dataset = load_tokenized_file(eval_file)
        eval_dataset = [format_data(entry) for entry in eval_dataset.values()]  # ✅ Fixed

    train_model(dataset, tokenizer, eval_dataset)
