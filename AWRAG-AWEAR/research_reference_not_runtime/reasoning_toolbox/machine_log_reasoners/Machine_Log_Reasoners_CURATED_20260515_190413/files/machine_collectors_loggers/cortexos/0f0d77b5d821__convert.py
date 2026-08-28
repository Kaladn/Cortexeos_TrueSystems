import os
import json
import csv
from pathlib import Path
from tqdm import tqdm
def main(input_path, output_path):
    log_path = output_path / "json_converter.log"
    logging.basicConfig(filename=log_path, level=logging.INFO)

    for file in input_path.glob("*.csv"):
        json_data = []
        try:
            with open(file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    json_data.append(row)
            out_file = output_path / f"{file.stem}.json"
            with open(out_file, 'w', encoding='utf-8') as j:
                json.dump(json_data, j, indent=2)
            logging.info(f"✅ Converted: {file.name}")
        except Exception as e:
            logging.error(f"❌ Error converting {file.name}: {e}")
            
def convert_files_to_jsonl():
    jsonl_data = []
    current_dir = os.getcwd()

    # Process TXT files
    txt_files = [file for file in os.listdir(current_dir) if file.endswith('.txt')]
    print(f"Found {len(txt_files)} txt files.")
    for txt_file in tqdm(txt_files, desc="Reading TXT files"):
        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read().strip()
            jsonl_data.append({"prompt": "", "completion": content})

    # Process CSV files
    csv_files = [file for file in os.listdir(current_dir) if file.endswith('.csv')]
    print(f"Found {len(csv_files)} csv files.")
    for csv_file in tqdm(csv_files, desc="Reading CSV files"):
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as file:
            reader = csv.DictReader(file)
            if 'prompt' in reader.fieldnames and 'completion' in reader.fieldnames:
                for row in reader:
                    jsonl_data.append({"prompt": row['prompt'], "completion": row['completion']})
            else:
                # Treat each row as a completion if structure unknown
                file.seek(0)
                reader = csv.reader(file)
                for row in reader:
                    jsonl_data.append({"prompt": "", "completion": row[0] if row else ""})

    # Write to JSONL
    output_file = os.path.join(current_dir, 'training_data.jsonl')
    with open(output_file, 'w', encoding='utf-8') as jsonl:
        for entry in tqdm(jsonl_data, desc="Writing JSONL"):
            jsonl.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Converted {len(jsonl_data)} entries into training_data.jsonl")

if __name__ == "__main__":
    convert_files_to_jsonl()