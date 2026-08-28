import os

# Base directory
base_dir = "A:/Symbolis"

# Define the directory structure
directories = [
    "data",
    "data/backup",
    "src",
    "modules",
    "tests",
    "tests/test_samples",
    "logs",
    "config",
    "docs",
    "venv"
]

# Create directories
for directory in directories:
    os.makedirs(os.path.join(base_dir, directory), exist_ok=True)

# Create placeholder files
files = {
    "data/word_list.txt": "",
    "data/symbolis_dict.json": "{}",
    "data/used_symbols.json": "{}",
    "data/unrecognized_words.json": "{}",
    "logs/symbolis_log.txt": "Symbolis Log File\n",
    "config/settings.json": """
{
    "symbol_size": {
        "common_words": 1,
        "medium_words": 3,
        "rare_words": 4
    },
    "preserve_capitalization": true,
    "default_output_format": "json"
}
""",
    "docs/README.md": "# Symbolis Project\n\nThis is the documentation for the Symbolis system.",
    "docs/SYMBOLIS_SPEC.md": "# Symbolis Specification\n\nTechnical breakdown of Symbolis.",
    "requirements.txt": "numpy\npandas\njson\n"
}

# Write placeholder files
for file_path, content in files.items():
    with open(os.path.join(base_dir, file_path), "w", encoding="utf-8") as f:
        f.write(content)

print(f"✅ Symbolis directory structure successfully created at {base_dir}")
