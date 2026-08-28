import os
import json
import torch
from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

# ✅ Paths
MODEL_PATH = r"A:/CortexBERT"
TOKENIZED_DATA_PATH = r"A:/Compression Engine/tokenized_dictionary"
SAVE_PATH = r"A:/CortexBERT-Trained"

# ✅ Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)

# ✅ Function to Load Pre-Tokenized Data
def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ Function to Train Cortex BERT
def train_on_files():
    for filename in sorted(os.listdir(TOKENIZED_DATA_PATH)):  # Sort A-Z
        if filename.endswith(".json"):
            file_path = os.path.join(TOKENIZED_DATA_PATH, filename)
            print(f"\n🔄 Training on: {filename}")

            # Load data
            data = load_data(file_path)
            input_ids = torch.tensor([entry["input_ids"] for entry in data], dtype=torch.long)
            labels = torch.tensor([entry["labels"] for entry in data], dtype=torch.long)

            # Convert to dataset
            dataset = TensorDataset(input_ids, labels)
            dataloader = DataLoader(dataset, batch_size=2, shuffle=True)  # ✅ Optimize batch size
            
            # Load Model
            model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True)

            # Training Arguments
            training_args = TrainingArguments(
                output_dir=SAVE_PATH,
                per_device_train_batch_size=1,  
                num_train_epochs=3,  
                save_strategy="epoch",
                save_total_limit=1,
                logging_dir=f"{SAVE_PATH}/logs",
                no_cuda=True,  # ✅ CPU Training for now
                remove_unused_columns=False,
            )

            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=dataset,
                tokenizer=tokenizer,
            )

            print(f"🚀 Training Cortex BERT on {filename}...")
            trainer.train()

            # Save Progress
            model.save_pretrained(SAVE_PATH)
            tokenizer.save_pretrained(SAVE_PATH)
            print(f"✅ Finished training {filename}, model saved!")

# ✅ Start Training
train_on_files()
