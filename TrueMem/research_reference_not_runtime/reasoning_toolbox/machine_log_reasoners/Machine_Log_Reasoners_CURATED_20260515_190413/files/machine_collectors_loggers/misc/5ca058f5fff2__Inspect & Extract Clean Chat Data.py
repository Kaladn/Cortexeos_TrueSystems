import os

# Define input and output paths
INPUT_FILE = r"C:\Users\mydyi\OneDrive\Documents\Desktop\Symbolis Mainport\Large Databases-Compressed\ChatGPT Historical Data\clean_conversations.txt"
OUTPUT_DIR = os.path.join(os.path.dirname(INPUT_FILE), "split_conversations")

# Number of parts to split into
NUM_PARTS = 20

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def split_file(input_file, output_dir, num_parts):
    """Splits a large text file into num_parts while keeping conversations intact."""
    
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    lines_per_part = total_lines // num_parts
    
    print(f"Total lines: {total_lines}")
    print(f"Lines per file: {lines_per_part}")
    
    part = 1
    line_count = 0
    buffer = []
    
    for line in lines:
        buffer.append(line)
        line_count += 1

        # Ensure we split at a conversation boundary (avoid cutting conversations)
        if line.startswith("🔹 Conversation") and line_count >= lines_per_part and part < num_parts:
            output_path = os.path.join(output_dir, f"conversation_part_{part:02d}.txt")
            
            with open(output_path, "w", encoding="utf-8") as out_f:
                out_f.writelines(buffer)
            
            print(f"Saved: {output_path} ({len(buffer)} lines)")
            
            buffer = []
            line_count = 0
            part += 1

    # Save the last remaining chunk
    if buffer:
        output_path = os.path.join(output_dir, f"conversation_part_{part:02d}.txt")
        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.writelines(buffer)
        print(f"Saved: {output_path} ({len(buffer)} lines)")

    print("✅ Splitting complete!")

# Run the function
split_file(INPUT_FILE, OUTPUT_DIR, NUM_PARTS)
