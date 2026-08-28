import requests
from pymongo import MongoClient
from transformers import pipeline

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["AI_Memory"]
collection = db["chat_history"]

# CortexBERT for Query Optimization
cortexbert_nnlp = pipeline("feature-extraction", model="CortexBERT")

# LM Studio API
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MAIN_MODEL = "mathstral-7b-v0.1"
DRAFT_MODEL = "llama-3.2-1b"  # Optional for speculative decoding

def retrieve_past_conversations(user_input, limit=5):
    """Fetch past relevant chat interactions from MongoDB."""
    past_messages = collection.find().sort("_id", -1).limit(limit)
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in past_messages])

def optimize_query(user_input):
    """Refine the user query using CortexBERT."""
    intent_analysis = cortexbert_nnlp(user_input)
    refined_query = f"Optimized Query: {user_input}\nIntent: {intent_analysis}"
    return refined_query

def generate_response(user_input):
    """Retrieve memory, optimize prompt, and send query to Mathstral-7B."""
    
    # Retrieve past memory
    past_context = retrieve_past_conversations(user_input)
    
    # Optimize query
    optimized_query = optimize_query(user_input)
    
    # Create enhanced prompt with memory
    full_prompt = f"{past_context}\nUser: {optimized_query}\nAI:"
    
    # Send query to LM Studio
    payload = {
        "model": MAIN_MODEL,
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.7,
        "max_tokens": 300,
        "speculative_model": DRAFT_MODEL  # Enable speculative decoding
    }
    
    response = requests.post(LM_STUDIO_URL, json=payload)
    
    if response.status_code == 200:
        response_text = response.json()["choices"][0]["message"]["content"]
    else:
        response_text = "Error retrieving response from LLM."

    # Store new interaction in memory
    collection.insert_one({"role": "user", "content": user_input})
    collection.insert_one({"role": "assistant", "content": response_text})
    
    return response_text

# Interactive Chat Loop
while True:
    user_query = input("You: ")
    if user_query.lower() in ["exit", "quit"]:
        break
    ai_response = generate_response(user_query)
    print(f"AI: {ai_response}\n")
