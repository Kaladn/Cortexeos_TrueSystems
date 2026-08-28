import os
import torch
import transformers
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model

# ✅ Model & Dataset Paths
MODEL_NAME = "A:/Qwen2.5-Math-1.5B"
DATASET_PATH = "A:/Compression Engine/merged_trainable_dataset.json"
OUTPUT_DIR = "A:/FineTuned_Qwen2.5"

# ✅ Disable Multi-processing & Enable Full RAM Usage
def tokenize_function(example):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return tokenizer(
        example["input"], 
        truncation=True, 
        padding="max_length", 
        max_length=256
    )

if __name__ == '__main__':
    print("🔄 Loading Model & Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.bfloat16)

    print("🔄 Loading Dataset into RAM...")
    dataset = load_dataset(
        "json", 
        data_files=DATASET_PATH, 
        split="train", 
        cache_dir=None,  # Prevents writing to disk
        keep_in_memory=True  # ✅ Full RAM utilization
    )

    print("🔄 Tokenizing Dataset (Single-Threaded)...")
    dataset = dataset.map(tokenize_function, num_proc=1, load_from_cache_file=False)

    # ✅ LoRA Config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)

    # ✅ Training Arguments (Optimized for CPU)
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=128,
        gradient_accumulation_steps=4,
        learning_rate=5e-4,
        num_train_epochs=3,
        logging_dir="./logs",
        save_total_limit=2,
        save_steps=1000,
        fp16=False,
        bf16=True,  # ✅ Enables `bfloat16` for faster CPU training
        dataloader_num_workers=0,  # ✅ No multiprocessing
        disable_tqdm=False,
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )

    print("🚀 Starting Training...")
    trainer.train()

    print("\n✅ Training Completed! Fine-tuned model saved at:", OUTPUT_DIR)
