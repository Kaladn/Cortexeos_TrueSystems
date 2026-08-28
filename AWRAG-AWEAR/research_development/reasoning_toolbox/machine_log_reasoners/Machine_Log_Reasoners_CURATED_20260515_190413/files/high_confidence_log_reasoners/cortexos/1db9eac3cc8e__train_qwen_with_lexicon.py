import os
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import Dataset
from peft import get_peft_model, LoraConfig, TaskType

# ✅ Paths
MODEL_PATH = r"A:/Qwen2.5-Math-1.5B"
SAVE_PATH = r"A:/Compression Engine/Qwen2.5-Trained"
TOKENIZED_DIR = r"A:/Compression Engine/tokenized_dictionary"  # ✅ Directory of tokenized A-Z JSONs

# ✅ Allow manual file selection
def select_file():
    files = os.listdir(TOKENIZED_DIR)
    json_files = [f for f in files if f.endswith(".json")]

    if not json_files:
        print("❌ No JSON files found in the directory!")
        return None

    print("\n📂 Available Tokenized Files:")
    for idx, file in enumerate(json_files, 1):
        print(f"  {idx}. {file}")

    while True:
        try:
            choice = int(input("\n🔍 Select a file number to load: ")) - 1
            if 0 <= choice < len(json_files):
                return os.path.join(TOKENIZED_DIR, json_files[choice])
            else:
                print("❌ Invalid choice. Try again.")
        except ValueError:
            print("❌ Enter a number!")

# ✅ Load & Validate JSON
def load_json(file_path):
    print(f"\n🔄 Loading: {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("❌ ERROR: JSON file must contain a list of entries!")
        if "input_ids" not in data[0]:
            raise ValueError("❌ ERROR: Missing 'input_ids' in JSON file!")

        print(f"✅ Loaded {len(data)} entries from {os.path.basename(file_path)}")
        return data
    except json.JSONDecodeError:
        print("❌ JSON file is corrupted or improperly formatted!")
        return None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return None

# ✅ Training Function
def train_model(dataset):
    print("🔄 Loading Model...")
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True)

    # ✅ LoRA Configuration
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
        per_device_train_batch_size=2,  # ✅ Adjust as needed
        num_train_epochs=3,  
        save_strategy="epoch",
        save_total_limit=1,
        logging_dir=f"{SAVE_PATH}/logs",
        report_to="none",
        no_cuda=True,
        remove_unused_columns=False,
    )

    # ✅ Data Collator (Ensures Padding)
    def causal_lm_collator(data):
        return {
            "input_ids": torch.tensor([f["input_ids"] for f in data], dtype=torch.long),
            "labels": torch.tensor([f["labels"] for f in data], dtype=torch.long),
            "attention_mask": torch.tensor([f["attention_mask"] for f in data]) if "attention_mask" in data[0] else None,
        }

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=Dataset.from_list(dataset),
        data_collator=causal_lm_collator,
    )

    print("🚀 Starting Training...")
    trainer.train()
    print("✅ Training Complete!")

    print("💾 Saving Model...")
    model.save_pretrained(SAVE_PATH)
    print(f"✅ Model Saved at {SAVE_PATH} 🎉")

# ✅ Main Execution
if __name__ == "__main__":
    selected_file = select_file()
    if selected_file:
        dataset = load_json(selected_file)
        if dataset:
            train_model(dataset)
