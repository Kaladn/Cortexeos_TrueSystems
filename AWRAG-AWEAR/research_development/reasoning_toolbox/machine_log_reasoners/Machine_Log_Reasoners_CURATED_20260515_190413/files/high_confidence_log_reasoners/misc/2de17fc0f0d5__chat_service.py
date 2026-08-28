from transformers import pipeline

class ChatService:
    def __init__(self):
        self.generator = pipeline("text-generation", model="gpt-3")

    def process_message(self, message, session_id):
        """
        Generate a response for the given message and session.
        """
        result = self.generator(message, max_length=150, num_return_sequences=1)
        return result[0]["generated_text"]
