import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import re
import threading

class WordRelationshipViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Word Relationship Viewer")
        self.root.geometry("1200x700")
        
        self.text_data = ""
        self.word_positions = {}
        
        self.create_ui()

    def create_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(top_frame, text="Open", command=self.open_file).pack(side=tk.LEFT)
        tk.Button(top_frame, text="Save", command=self.save_file).pack(side=tk.LEFT)
        tk.Button(top_frame, text="Edit Directory", command=self.edit_directory).pack(side=tk.LEFT)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.before_listbox = tk.Listbox(main_frame, width=20)
        self.before_listbox.pack(side=tk.LEFT, fill=tk.Y)

        self.words_listbox = tk.Listbox(main_frame, width=20)
        self.words_listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.words_listbox.bind("<<ListboxSelect>>", self.show_word_details)

        self.word_count_listbox = tk.Listbox(main_frame, width=15)
        self.word_count_listbox.pack(side=tk.LEFT, fill=tk.Y)

        self.after_listbox = tk.Listbox(main_frame, width=20)
        self.after_listbox.pack(side=tk.LEFT, fill=tk.Y)

        self.position_listbox = tk.Listbox(main_frame, width=20)
        self.position_listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.position_listbox.bind("<Double-Button-1>", self.jump_to_position)

        self.text_area = scrolledtext.ScrolledText(self.root, height=10)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as file:
                self.text_data = file.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", self.text_data)
            threading.Thread(target=self.analyze_text).start()

    def analyze_text(self):
        words = re.findall(r'\b[a-zA-Z0-9]+\b', self.text_data.lower())
        word_counts = {}
        self.word_positions = {}

        for idx, word in enumerate(words):
            word_counts[word] = word_counts.get(word, 0) + 1
            self.word_positions.setdefault(word, []).append(idx)

        sorted_words = sorted(word_counts.items(), key=lambda x: x[1])

        self.words_listbox.delete(0, tk.END)
        self.word_count_listbox.delete(0, tk.END)

        for word, count in sorted_words:
            self.words_listbox.insert(tk.END, word)
            self.word_count_listbox.insert(tk.END, count)

    def show_word_details(self, event):
        selection = self.words_listbox.curselection()
        if not selection:
            return

        selected_word = self.words_listbox.get(selection[0])
        positions = self.word_positions.get(selected_word, [])
        words = re.findall(r'\b[a-zA-Z0-9]+\b', self.text_data.lower())

        before_words, after_words = {}, {}
        self.before_listbox.delete(0, tk.END)
        self.after_listbox.delete(0, tk.END)
        self.position_listbox.delete(0, tk.END)

        for pos in positions:
            line_num = self.text_data.count('\n', 0, self.text_data.find(words[pos])) + 1
            word_num = pos - self.text_data.rfind('\n', 0, self.text_data.find(words[pos]))
            self.position_listbox.insert(tk.END, f"Line {line_num}, Word {word_num}")

            if pos > 0:
                bw = words[pos - 1]
                before_words[bw] = before_words.get(bw, 0) + 1
            if pos < len(words) - 1:
                aw = words[pos + 1]
                after_words[aw] = after_words.get(aw, 0) + 1

        for bw, count in sorted(before_words.items(), key=lambda x: -x[1]):
            self.before_listbox.insert(tk.END, f"{bw} ({count})")

        for aw, count in sorted(after_words.items(), key=lambda x: -x[1]):
            self.after_listbox.insert(tk.END, f"{aw} ({count})")

    def jump_to_position(self, event):
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = WordRelationshipViewer(root)
    root.mainloop()
