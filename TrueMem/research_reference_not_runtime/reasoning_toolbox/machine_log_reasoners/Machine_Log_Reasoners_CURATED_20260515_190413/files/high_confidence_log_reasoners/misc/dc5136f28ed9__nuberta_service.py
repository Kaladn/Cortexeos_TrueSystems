from models.nuberta.nuberta import NuBERTa
from transformers import AutoTokenizer
import torch

# Load NuBERTa model and tokenizer
nuberta_model = NuBERTa().to("cuda")  # Ensure CUDA is available if using GPU
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

def process_with_nuberta(message, context=""):
    inputs = tokenizer(
        context + "\nUser: " + message,
        return_tensors="pt",
        padding=True,
        truncation=True
    ).to("cuda")

    with torch.no_grad():
        outputs = nuberta_model(**inputs)

    return parse_nuberta_response(outputs)

def parse_nuberta_response(outputs):
    # Example placeholder: adapt based on your model's output format
    response_text = "AI response based on outputs"  # Replace with actual logic
    return response_text
