import dearpygui.dearpygui as dpg
import re
import os

# Global storage
document_text = ""
word_positions = {}
recent_files = []  # Stores last 5 opened files


def load_file(file_path):
    """Loads a document and processes text."""
    global document_text, word_positions

    file_path = file_path.strip('"')  # Remove any accidental extra quotes

    if not os.path.exists(file_path):
        dpg.set_value("status_text", f"⚠️ ERROR: File not found: {file_path}")
        return

    try:
        # Try different encodings to avoid errors
        with open(file_path, "r", encoding="utf-8") as file:
            document_text = file.read()
        
        # ✅ Update UI
        dpg.set_value("doc_display", document_text)
        dpg.set_value("file_path_display", file_path)
        dpg.set_value("status_text", f"📄 Loaded: {os.path.basename(file_path)}")

        # ✅ Process text
        process_text(document_text)

        # ✅ Save to recent files list
        update_recent_files(file_path)

    except Exception as e:
        dpg.set_value("status_text", f"❌ ERROR: {e}")


def process_text(text):
    """Processes the document and finds word relationships."""
    global word_positions
    words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
    word_positions.clear()

    for idx, word in enumerate(words):
        word_positions.setdefault(word, []).append(idx)

    dpg.delete_item("word_list", children_only=True)
    for word, positions in sorted(word_positions.items(), key=lambda x: len(x[1]), reverse=True):
        dpg.add_button(label=f"{word} ({len(positions)})", parent="word_list", callback=highlight_word, user_data=word)


def highlight_word(sender, app_data, user_data):
    """Highlights selected words in the document."""
    word = user_data
    positions = word_positions.get(word, [])

    if positions:
        dpg.set_value("doc_display", document_text)
        highlighted_text = document_text
        for pos in positions[:10]:  # Only highlight first 10 occurrences
            highlighted_text = highlighted_text.replace(word, f"**{word}**", 1)
        dpg.set_value("doc_display", highlighted_text)


def update_recent_files(file_path):
    """Keeps a list of the last 5 opened files."""
    global recent_files
    if file_path not in recent_files:
        recent_files.insert(0, file_path)
    recent_files = recent_files[:5]  # Keep only 5 items

    # Update UI List
    dpg.delete_item("recent_files_list", children_only=True)
    for recent in recent_files:
        dpg.add_button(label=os.path.basename(recent), parent="recent_files_list", callback=lambda: load_file(recent))


def file_drop_callback(sender, app_data):
    """Handles drag-and-drop file loading."""
    file_path = app_data.strip('"')
    load_file(file_path)


# ✅ UI Creation
dpg.create_context()
dpg.create_viewport(title='AI-Powered Document Reader', width=1100, height=700)

with dpg.window(tag="main_window"):
    dpg.add_text("📂 Open a Document:", bullet=True)

    # ✅ File selection buttons
    dpg.add_button(label="📁 Open File", callback=lambda: dpg.show_item("file_dialog"))
    dpg.add_input_text(label="File Path", tag="file_path_display", readonly=True)

    dpg.add_separator()

    # ✅ Drag-and-Drop Area for Files
    with dpg.group():
        dpg.add_text("⬇️ Drag a file here ⬇️", tag="drag_drop_text")

        with dpg.drag_payload(parent="drag_drop_text", drag_data_type="text", callback=file_drop_callback):
            dpg.add_text("Drop file here")

    dpg.add_separator()

    # ✅ Recent files list
    dpg.add_text("📜 Recent Files:", bullet=True)
    with dpg.child_window(tag="recent_files_list", width=250, height=150):
        dpg.add_text("No recent files")

    dpg.add_separator()

    # ✅ Word list
    with dpg.child_window(tag="word_list", width=250, height=500):
        dpg.add_text("Word List:")

    # ✅ Document display
    with dpg.child_window(tag="doc_window", width=800, height=600, pos=[260, 0]):
        dpg.add_text(default_value="📖 Document will appear here...", tag="doc_display", wrap=700)

    dpg.add_separator()

    # ✅ Status message area
    dpg.add_text("", tag="status_text")

# ✅ File Dialog for manual selection
dpg.add_file_dialog(directory_selector=False, show=False, callback=lambda s, a: load_file(a['file_path_name']), tag="file_dialog")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
