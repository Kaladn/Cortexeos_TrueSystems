import os
import ast
import json
import shutil
from tqdm import tqdm

# === CONFIGURATION ===
USER = os.getlogin()
REWRITTEN_DIR = f"C:/Users/{USER}/Desktop/Rewritten/"
PSEUDO_DIR = f"C:/Users/{USER}/Desktop/PseudoCode/"
MARKED_FILE = f"C:/Users/{USER}/Desktop/MarkedForDeletion.txt"
ROOT_DIRS = ["C:/", "D:/"]  # You can adjust your drives here

# === MAKE SURE DIRECTORIES EXIST ===
os.makedirs(REWRITTEN_DIR, exist_ok=True)
os.makedirs(PSEUDO_DIR, exist_ok=True)

# === FUNCTION TO EXTRACT FUNCTIONS FROM A FILE ===
def extract_functions(source_code):
    functions = []
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(ast.get_source_segment(source_code, node))
    except Exception as e:
        pass
    return functions

# === FUNCTION TO TRY FIXING SYNTAX ERRORS ===
def try_fix(file_path):
    tries = 0
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    while tries < 10:
        try:
            ast.parse(content)
            return content, True
        except SyntaxError as e:
            line = e.lineno
            if not line:
                break
            lines = content.split('\n')
            if line - 1 < len(lines):
                lines.pop(line - 1)  # Remove faulty line
                content = '\n'.join(lines)
            tries += 1
    return content, False

# === FUNCTION TO CREATE PSEUDO-CODE FROM FUNCTIONS ===
def generate_pseudo(functions):
    pseudo_list = []
    for func in functions:
        first_line = func.strip().split('\n')[0]
        pseudo_list.append(f"# Pseudo: {first_line}")
    return '\n'.join(pseudo_list)

# === MAIN SCAN FUNCTION ===
def scan_files():
    marked = []

    python_files = []
    for root_dir in ROOT_DIRS:
        for dirpath, dirs, files in os.walk(root_dir):
            # Skip common third-party folders
            if 'env' in dirpath.lower() or 'site-packages' in dirpath.lower():
                continue
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(dirpath, file))

    print(f"[INFO] Total Python files to scan: {len(python_files)}")

    for file_path in tqdm(python_files, desc="Scanning Files"):
        try:
            fixed_content, success = try_fix(file_path)

            if success:
                functions = extract_functions(fixed_content)
                if functions:
                    # Save fixed file
                    filename = os.path.basename(file_path)
                    new_path = os.path.join(REWRITTEN_DIR, filename)
                    with open(new_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                else:
                    marked.append(file_path)
                    pseudo = generate_pseudo(functions)
                    pseudo_name = os.path.basename(file_path).replace('.py', '_pseudo.py')
                    pseudo_path = os.path.join(PSEUDO_DIR, pseudo_name)
                    with open(pseudo_path, 'w', encoding='utf-8') as f:
                        f.write(pseudo)
            else:
                marked.append(file_path)
                pseudo = generate_pseudo(extract_functions(fixed_content))
                pseudo_name = os.path.basename(file_path).replace('.py', '_pseudo.py')
                pseudo_path = os.path.join(PSEUDO_DIR, pseudo_name)
                with open(pseudo_path, 'w', encoding='utf-8') as f:
                    f.write(pseudo)

        except Exception as e:
            marked.append(file_path)

    # Save marked list
    with open(MARKED_FILE, 'w', encoding='utf-8') as f:
        for item in marked:
            f.write(item + '\n')

    print("[DONE] All files processed.")
    print(f"Rewritten files saved to: {REWRITTEN_DIR}")
    print(f"Pseudo-code files saved to: {PSEUDO_DIR}")
    print(f"Marked files listed in: {MARKED_FILE}")

# === RUN ===
if __name__ == "__main__":
    scan_files()
