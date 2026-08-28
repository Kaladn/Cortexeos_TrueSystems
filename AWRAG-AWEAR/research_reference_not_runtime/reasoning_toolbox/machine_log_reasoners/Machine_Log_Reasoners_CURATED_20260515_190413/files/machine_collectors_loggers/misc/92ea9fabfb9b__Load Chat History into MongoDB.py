from pymongo import MongoClient
import json

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["AI_Memory"]
collection = db["chat_history"]

# Load cleaned JSON
json_file = "C:/Users/mydyi/Documents/Symbolis_Mainport/cleaned_conversations.json"
with open(json_file, "r", encoding="utf-8") as file:
    chat_data = json.load(file)

# Insert chat history into MongoDB
collection.insert_many(chat_data)

print(f"✅ Successfully loaded {len(chat_data)} messages into MongoDB!")
