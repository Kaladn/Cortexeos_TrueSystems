
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import re
import random

CONFIG_FILE = "profanity_thesaurus.json"

class ProfanityUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Cortex Profanity Filter - Tinkerture Mode")
        self.replacements = {}
        self.selected_file = None

        self.setup_widgets()
        self.load_config()

    def setup_widgets(self):
        self.table_frame = ttk.Frame(self.master)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(self.table_frame, columns=("Word", "Replacements"), show="headings")
        self.tree.heading("Word", text="Profane Word")
        self.tree.heading("Replacements", text="Replacement Options")
        self.tree.pack(fill="both", expand=True)

        self.entry_frame = ttk.Frame(self.master)
        self.entry_frame.pack(fill="x", padx=10)

        self.word_entry = ttk.Entry(self.entry_frame, width=20)
        self.word_entry.grid(row=0, column=0, padx=5, pady=5)
        self.replace_entry = ttk.Entry(self.entry_frame, width=40)
        self.replace_entry.grid(row=0, column=1, padx=5, pady=5)
        self.add_btn = ttk.Button(self.entry_frame, text="Add/Update", command=self.add_word)
        self.add_btn.grid(row=0, column=2, padx=5)

        self.file_frame = ttk.Frame(self.master)
        self.file_frame.pack(fill="x", padx=10)

        self.file_label = ttk.Label(self.file_frame, text="No file selected")
        self.file_label.pack(side="left", padx=5)

        self.browse_btn = ttk.Button(self.file_frame, text="Select File", command=self.select_file)
        self.browse_btn.pack(side="right", padx=5)

        self.button_frame = ttk.Frame(self.master)
        self.button_frame.pack(fill="x", pady=10)

        self.load_btn = ttk.Button(self.button_frame, text="Load Config", command=self.load_config)
        self.load_btn.pack(side="left", padx=10)

        self.save_btn = ttk.Button(self.button_frame, text="Save Config", command=self.save_config)
        self.save_btn.pack(side="left")

        self.run_btn = ttk.Button(self.button_frame, text="Run Filter", command=self.run_filter)
        self.run_btn.pack(side="right", padx=10)

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("All Text Files", "*.jsonl *.txt")])
        if file_path:
            self.selected_file = file_path
            self.file_label.config(text=os.path.basename(file_path))

    def load_config(self):
        self.tree.delete(*self.tree.get_children())
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.replacements = json.load(f)
            for word, subs in self.replacements.items():
                self.tree.insert('', 'end', values=(word, ", ".join(subs)))
        else:
            self.replacements = {}

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.replacements, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Saved", "Configuration saved successfully!")

    def add_word(self):
        word = self.word_entry.get().strip().lower()
        subs = [s.strip() for s in self.replace_entry.get().split(',') if s.strip()]
        if not word or not subs:
            messagebox.showerror("Error", "Please enter both a word and at least one replacement.")
            return
        self.replacements[word] = subs
        self.load_config()
        self.word_entry.delete(0, 'end')
        self.replace_entry.delete(0, 'end')

    def run_filter(self):
        if not self.selected_file:
            messagebox.showwarning("No File", "Please select a file first.")
            return

        try:
            base, ext = os.path.splitext(self.selected_file)
            output_file = f"{base}_cleaned{ext}"

            if ext == ".jsonl":
                with open(self.selected_file, 'r', encoding='utf-8') as infile,                      open(output_file, 'w', encoding='utf-8') as outfile:
                    for line in infile:
                        try:
                            item = json.loads(line)
                            if 'completion' in item:
                                item['completion'] = self.replace_profanity(item['completion'])
                            outfile.write(json.dumps(item, ensure_ascii=False) + "\n")
                        except json.JSONDecodeError:
                            continue

            elif ext == ".txt":
                with open(self.selected_file, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                cleaned = self.replace_profanity(content)
                with open(output_file, 'w', encoding='utf-8') as outfile:
                    outfile.write(cleaned)
            else:
                messagebox.showerror("Unsupported Format", "Only .jsonl and .txt files are supported right now.")
                return

            messagebox.showinfo("Done", f"Cleaned file saved as:\n{output_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run filter:\n{e}")

    def replace_profanity(self, text):
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(word) for word in self.replacements.keys()) + r")\b",
            flags=re.IGNORECASE
        )

        def replacement(match):
            word = match.group(0).lower()
            replacements = self.replacements.get(word, [])
            return random.choice(replacements) if replacements else word

        return pattern.sub(replacement, text)

if __name__ == "__main__":
    root = tk.Tk()
    app = ProfanityUI(root)
    root.mainloop()
