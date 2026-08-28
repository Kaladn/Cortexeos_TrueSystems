import os
import re

def clean_text_file(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        cleaned_content = re.sub(r'[^a-zA-Z\s\n]', '', content)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        print(f"✅ Cleaned: {input_file} -> {output_file}")
    except Exception as e:
        print(f"⚠️ Error processing {input_file}: {e}")

def process_all_txt_files(start_dir):
    found_files = False
    for root, _, files in os.walk(start_dir):
        for file in files:
            if file.endswith('.txt'):
                found_files = True
                input_path = os.path.join(root, file)
                output_path = os.path.join(root, file.replace('.txt', '_cleaned.txt'))
                clean_text_file(input_path, output_path)
    if not found_files:
        print("⚠️ No .txt files found!")

if __name__ == '__main__':
    current_dir = os.getcwd()
    print(f"📂 Scanning directory: {current_dir}")
    process_all_txt_files(current_dir)
    print("🎯 Done! Check for *_cleaned.txt files.")
