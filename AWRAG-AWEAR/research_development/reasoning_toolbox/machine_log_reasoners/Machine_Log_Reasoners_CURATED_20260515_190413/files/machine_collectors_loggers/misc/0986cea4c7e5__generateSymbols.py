import os

def generate_symbols(byte_size, num_symbols, output_file, start_from=0):
    """Generate symbols in chunks to prevent memory overload."""
    with open(output_file, "ab") as f:  # Append binary mode to continue from last marker
        for i in range(start_from, start_from + num_symbols):
            f.write(i.to_bytes(byte_size, 'big'))  # Write symbol as raw bytes
        print(f"✅ {num_symbols} symbols saved to {output_file} from index {start_from}.")

    # Update marker file to track progress
    with open(f"{output_file}.marker", "w") as marker_file:
        marker_file.write(str(start_from + num_symbols))

def load_last_position(output_file):
    """Load the last generated position from the marker file."""
    marker_file = f"{output_file}.marker"
    if os.path.exists(marker_file):
        with open(marker_file, "r") as f:
            return int(f.read().strip())
    return 0

def main():
    output_dir = "symbols"
    os.makedirs(output_dir, exist_ok=True)

    # Generate incrementally (2M symbols at a time)
    num_symbols_per_run = 2000000  

    files_to_generate = [
        ("symbols_1byte.bin", 1, 256),
        ("symbols_2byte.bin", 2, 65536),
        ("symbols_3byte.bin", 3, 16777216),
        ("symbols_4byte.bin", 4, 4294967296),
    ]

    for filename, byte_size, total_symbols in files_to_generate:
        output_file = os.path.join(output_dir, filename)
        last_position = load_last_position(output_file)

        while last_position < total_symbols:
            generate_symbols(byte_size, min(num_symbols_per_run, total_symbols - last_position), output_file, last_position)
            last_position = load_last_position(output_file)  # Update position for next run

def add_special_symbols(special_words, output_file):
    """Generate special class symbols (law, science, etc.)."""
    with open(output_file, "wb") as f:
        for idx, word in enumerate(special_words):
            symbol = idx.to_bytes(2, 'big')  # Assign a 2-byte symbol
            f.write(symbol)
        print(f"✅ Special class symbols saved to {output_file}")

if __name__ == "__main__":
    main()

    # Example of adding special category symbols
    special_classes = ["Quantum", "NeuralNet", "AI", "Patent", "Legal", "DNA", "Protein"]
    add_special_symbols(special_classes, "symbols/special_symbols.bin")

