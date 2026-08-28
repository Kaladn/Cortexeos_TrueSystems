import sys
import faiss
import numpy as np
import pickle
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QLabel, QProgressBar
from sentence_transformers import SentenceTransformer

# **CONFIGURATION**
FAISS_INDEX_PATH = r"C:\Users\mydyi\Desktop\Conversation splitter\faiss_index.bin"
MESSAGES_PKL_PATH = r"C:\Users\mydyi\Desktop\Conversation splitter\faiss_index_messages.pkl"

# **FORCE-LOAD FAISS INDEX**
def load_faiss_index(index_path):
    if os.path.exists(index_path):
        print(f"✅ FAISS Index Loaded: {index_path}")
        return faiss.read_index(index_path)
    else:
        print(f"❌ FAISS Index NOT FOUND: {index_path}")
        sys.exit(1)

# **FORCE-LOAD MESSAGE MAPPINGS**
def load_messages(messages_path):
    if os.path.exists(messages_path):
        print(f"✅ Message Data Loaded: {messages_path}")
        with open(messages_path, "rb") as f:
            return pickle.load(f)
    else:
        print(f"❌ Message File MISSING: {messages_path}")
        sys.exit(1)

# **LOAD SBERT MODEL**
print("🔄 Loading SBERT Model...")
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# **LOAD EVERYTHING INTO MEMORY**
faiss_index = load_faiss_index(FAISS_INDEX_PATH)
messages = load_messages(MESSAGES_PKL_PATH)

# **UI APPLICATION**
class SearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Semantic Search UI")
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout()
        self.label = QLabel("Enter Search Query:")
        self.search_input = QLineEdit(self)
        self.search_button = QPushButton("Search")
        self.results_area = QTextEdit(self)
        self.progress = QProgressBar(self)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.search_input)
        self.layout.addWidget(self.search_button)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.results_area)

        self.search_button.clicked.connect(self.search)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def search(self):
        query = self.search_input.text().strip()
        if not query:
            self.results_area.setText("Enter a search query.")
            return

        self.progress.setValue(25)
        query_embedding = MODEL.encode([query])
        self.progress.setValue(50)

        # **FORCE SEARCH**
        distances, indices = faiss_index.search(np.array(query_embedding).astype('float32'), 5)
        self.progress.setValue(75)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(messages):
                results.append(f"🔹 {messages[idx]}")
            else:
                results.append(f"❌ INDEX OUT OF BOUNDS: {idx}")

        # **DISPLAY RESULTS**
        if results:
            self.results_area.setText("\n".join(results))
        else:
            self.results_area.setText("❌ NO MATCHES FOUND.")

        self.progress.setValue(100)

# **RUN APPLICATION**
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SearchApp()
    window.show()
    sys.exit(app.exec_())
