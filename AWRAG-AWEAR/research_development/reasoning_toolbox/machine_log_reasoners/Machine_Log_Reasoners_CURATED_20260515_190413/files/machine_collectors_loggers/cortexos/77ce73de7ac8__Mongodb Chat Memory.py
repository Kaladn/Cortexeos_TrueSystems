from pymongo import MongoClient
import datetime
import uuid

# ✅ MongoDB Connection Setup
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "AI_ChatMemory"
COLLECTION_NAME = "ChatLogs"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

class ChatMemory:
    def __init__(self):
        self.collection = collection

    def add_entry(self, user_id, role, content, context=None, subcontext=None, subsubcontext=None):
        """
        Stores a chat entry into MongoDB with a unique ID, timestamps, and hierarchical context.
        """
        entry = {
            "entry_id": str(uuid.uuid4()),  # Unique ID for each message
            "user_id": user_id,  # User-specific context
            "timestamp": datetime.datetime.utcnow(),
            "role": role,
            "content": content,
            "context": context or "",
            "subcontext": subcontext or "",
            "subsubcontext": subsubcontext or "",
            "changes": []  # Track changes
        }
        self.collection.insert_one(entry)
        return entry["entry_id"]

    def add_change(self, entry_id, change_description):
        """
        Appends a modification record to an existing chat log entry.
        """
        timestamp = datetime.datetime.utcnow()
        change = {"timestamp": timestamp, "description": change_description}
        
        self.collection.update_one(
            {"entry_id": entry_id},
            {"$push": {"changes": change}}
        )

    def get_log(self, user_id, limit=50):
        """
        Retrieves the latest chat logs for a user, sorted by timestamp.
        """
        return list(self.collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))
    
    def search_context(self, user_id, query):
        """
        Searches past conversations for relevant context.
        """
        return list(self.collection.find(
            {"user_id": user_id, "$text": {"$search": query}}
        ))

# ✅ Example Usage
if __name__ == "__main__":
    chat_memory = ChatMemory()
    user_id = "user_123"

    # ✅ Store Messages
    entry1 = chat_memory.add_entry(user_id, "user", "What is AI?", "AI Basics")
    entry2 = chat_memory.add_entry(user_id, "assistant", "AI stands for Artificial Intelligence...", "AI Basics")

    # ✅ Modify an Entry
    chat_memory.add_change(entry2, "Added a detailed explanation about AI types.")
    
    # ✅ Retrieve Latest Logs
    logs = chat_memory.get_log(user_id, limit=5)
    for log in logs:
        print(f"{log['timestamp']} - {log['role']}: {log['content']}")

    # ✅ Search Context
    relevant_chats = chat_memory.search_context(user_id, "AI")
    print("Relevant Past Conversations:", relevant_chats)
