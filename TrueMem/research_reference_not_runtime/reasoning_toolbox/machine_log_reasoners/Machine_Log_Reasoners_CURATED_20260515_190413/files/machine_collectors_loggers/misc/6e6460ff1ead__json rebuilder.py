import json
import os

# Define source and destination directories
source_directory = r"E:\Compression Engine\tokenized_dictionary"
destination_directory = os.path.join(os.path.expanduser("~"), "Desktop", "Processed_Tokenized_Dictionary")

# Ensure destination directory exists
os.makedirs(destination_directory, exist_ok=True)

def process_json_file(file_path, destination_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Remove words and only store hex and binary values
        cleaned_data = []
        for key in data.keys():
            if isinstance(data[key], dict) and "hex" in data[key] and "binary" in data[key]:
                cleaned_data.append({
                    "hex": data[key]["hex"],
                    "binary": data[key]["binary"]
                })

        # Save the cleaned version
        with open(destination_path, "w", encoding="utf-8") as file:
            json.dump(cleaned_data, file, indent=4, ensure_ascii=False)

        print(f"Processed and saved: {destination_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

# Process all JSON files in the source directory
for filename in os.listdir(source_directory):
    if filename.endswith(".json"):
        source_path = os.path.join(source_directory, filename)
        destination_path = os.path.join(destination_directory, filename)
        process_json_file(source_path, destination_path)

print("Processing complete. No words included.")
