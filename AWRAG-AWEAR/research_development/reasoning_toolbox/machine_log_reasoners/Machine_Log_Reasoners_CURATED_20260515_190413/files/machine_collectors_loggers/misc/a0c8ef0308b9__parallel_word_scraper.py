import os
import sys
import glob
import time
import shutil
import subprocess
import threading

sys.stdout.reconfigure(encoding='utf-8')  # Ensure Unicode prints correctly

# Configuration
SOURCE_DIR = "C:/Users/mydyi/OneDrive/Documents/Desktop/epub"  # Root folder with thousands of subdirectories
DATA_DIR = "C:/AI SYMBOLIS WORK/data"  # Temporary directory for processing
SCRAPED_DIR = "C:/AI SYMBOLIS WORK/data/scraped"  # Processed files go here
SCRIPT_PATH = "C:/AI SYMBOLIS WORK/input/parallel_word_scraper.py"  # Processing script
PYTHON_EXECUTABLE = "C:/AI SYMBOLIS WORK/scripts/.venv/Scripts/python.exe"  # Python environment
BATCH_SIZE = 500  # ⚡ Now moves 500 files per batch
WAIT_TIME = 1  # Pause time (lowered for speed)

def find_files():
    """Finds up to BATCH_SIZE .txt files across thousands of subdirectories."""
    files = []
    for subdir in os.scandir(SOURCE_DIR):  # Faster than os.listdir()
        if subdir.is_dir():  # Only process folders
            txt_files = glob.glob(os.path.join(subdir.path, "*.txt"))  # Find .txt files in subdir
            files.extend(txt_files)
            if len(files) >= BATCH_SIZE:
                break  # Stop once we reach batch size
    return files[:BATCH_SIZE]

def move_files_to_data(files):
    """Moves selected files to the DATA_DIR for processing using multithreading."""
    os.makedirs(DATA_DIR, exist_ok=True)

    def move_file(file):
        dest_path = os.path.join(DATA_DIR, os.path.basename(file))
        shutil.move(file, dest_path)
        print(f"📂 Moved {file} → {dest_path}")

    threads = []
    for file in files:
        t = threading.Thread(target=move_file, args=(file,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()  # Wait for all threads to finish

def run_processing_script():
    """Runs the word processing script asynchronously."""
    print("🚀 Running processing script...")
    
    process = subprocess.Popen(
        [PYTHON_EXECUTABLE, SCRIPT_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    for line in process.stdout:
        print(line, end="")  # Print script output live

    stderr_output = process.stderr.read()
    if stderr_output:
        print(f"❌ ERROR: {stderr_output}")

    process.wait()  # Ensure process fully completes
    print("✅ Processing script finished.")

def move_processed_files():
    """Moves processed files from DATA_DIR to SCRAPED_DIR using multithreading."""
    os.makedirs(SCRAPED_DIR, exist_ok=True)

    def move_file(file):
        dest_path = os.path.join(SCRAPED_DIR, os.path.basename(file))
        shutil.move(file, dest_path)
        print(f"✅ Processed and moved {file} → {dest_path}")

    files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    threads = []

    for file in files:
        t = threading.Thread(target=move_file, args=(file,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()  # Wait for all threads to finish

def process_batches():
    """Processes files in batches of 500 until all files are handled."""
    while True:
        files = find_files()
        if not files:
            print("🎉 All files have been processed!")
            break

        print(f"🔄 Found {len(files)} files to process...")
        move_files_to_data(files)
        run_processing_script()
        move_processed_files()
        
        # Estimate how many files remain
        remaining_files = sum(len(glob.glob(os.path.join(SOURCE_DIR, subdir, "*.txt"))) for subdir in os.listdir(SOURCE_DIR))
        print(f"📊 Estimated files left: {remaining_files}")

        print(f"⏳ Waiting {WAIT_TIME} seconds before the next batch...")
        time.sleep(WAIT_TIME)  # Lowered wait time for faster processing

if __name__ == "__main__":
    process_batches()
