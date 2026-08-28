import os
import tqdm

def split_large_file_with_progress(file_path, output_dir, chunk_size_mb=250):
    chunk_size = chunk_size_mb * 1024 * 1024  # Convert MB to bytes
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size // chunk_size) + 1

    os.makedirs(output_dir, exist_ok=True)
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        file_number = 1
        progress = tqdm.tqdm(total=file_size, unit='B', unit_scale=True, desc="📂 Splitting File")
        
        while True:
            start_pos = f.tell()
            chunk = f.read(chunk_size)
            end_pos = f.tell()
            if not chunk:
                break
            
            output_file = os.path.join(output_dir, f'split_{file_number}.txt')
            with open(output_file, 'w', encoding='utf-8') as out_f:
                out_f.write(chunk)
                
            progress.update(end_pos - start_pos)
            print(f"✅ Created {output_file}")
            file_number += 1
        
        progress.close()
    print("✅ Split complete!")

if __name__ == "__main__":
    # Example usage:
    file_path = input("Enter the full path to the large file: ")
    output_dir = input("Enter the output directory: ")
    split_large_file_with_progress(file_path, output_dir)
