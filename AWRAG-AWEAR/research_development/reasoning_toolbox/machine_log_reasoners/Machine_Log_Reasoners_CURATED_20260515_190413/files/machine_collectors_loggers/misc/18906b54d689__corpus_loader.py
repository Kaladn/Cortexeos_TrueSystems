import os
import uuid
from datetime import datetime

class CorpusLoader:
    def __init__(self, config):
        self.config = config

    def get_session_dir(self):
        """Determines the session directory based on the new file system rules."""
        today = datetime.now().strftime("%Y-%m-%d")
        session_uuid = str(uuid.uuid4())
        session_dir = os.path.join("memory", today, session_uuid)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def load_documents(self, doc_ids, corpus_id):
        """Loads raw text from documents and yields (doc_id, raw_text) pairs."""
        # This is a placeholder. In a real implementation, this would
        # connect to a document store and retrieve documents by ID.
        print(f"[CorpusLoader] Loading documents for corpus: {corpus_id}")
        for doc_id in doc_ids:
            # Simulate reading a document
            raw_text = f"This is the content of document {doc_id}."
            yield (doc_id, raw_text)

    def load_all_logs(self, session_dir):
        """Loads all .jsonl files from a given session directory."""
        print(f"[CorpusLoader] Loading all logs from: {session_dir}")
        for filename in os.listdir(session_dir):
            if filename.endswith(".jsonl"):
                filepath = os.path.join(session_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        yield (filename, line)
