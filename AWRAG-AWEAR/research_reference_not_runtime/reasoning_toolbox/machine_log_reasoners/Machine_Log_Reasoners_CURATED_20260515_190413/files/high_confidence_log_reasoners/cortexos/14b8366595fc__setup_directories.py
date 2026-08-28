import os

# Define base directory
base_dir = "A:/CortexBERT"

# List of required directories
directories = [
    "data",
    "data/raw",
    "data/processed",
    "data/tmx",   # For TMX language files
    "models",
    "training",
    "utils",
    "configs",
    "logs",
    "checkpoints",
    "deployment"
]

# Create directories
for dir in directories:
    path = os.path.join(base_dir, dir)
    os.makedirs(path, exist_ok=True)
    print(f"✅ Created: {path}")

print("\n🚀 All required directories are set up!")
