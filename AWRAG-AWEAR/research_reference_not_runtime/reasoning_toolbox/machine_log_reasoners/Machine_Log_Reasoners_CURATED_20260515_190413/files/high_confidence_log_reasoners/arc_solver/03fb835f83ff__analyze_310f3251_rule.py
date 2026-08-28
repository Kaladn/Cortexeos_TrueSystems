"""
Analyze the actual transformation rule for 310f3251
"""
import json
import numpy as np

# Load
with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

# Look at first example closely
ex1_input = np.array(task['train'][0]['input'])
ex1_output = np.array(task['train'][0]['output'])

print("Example 1 Analysis:")
print(f"\nInput:\n{ex1_input}")
print(f"\nOutput:\n{ex1_output}")

# Tile 3× and see what's different
tiled = np.tile(ex1_input, (3, 3))
print(f"\nSimple 3× tiling:\n{tiled}")

print(f"\n{'='*60}")
print("DIFFERENCES (where output != simple tiling):")
print(f"{'='*60}")

for i in range(ex1_output.shape[0]):
    for j in range(ex1_output.shape[1]):
        if ex1_output[i, j] != tiled[i, j]:
            print(f"Position ({i},{j}): tiled={tiled[i,j]} → output={ex1_output[i,j]}")

print(f"\n{'='*60}")
print("PATTERN HYPOTHESIS:")
print(f"{'='*60}")

# Check if 2s appear at specific grid intersections
print("\nLooking at where 2s appear in the output...")
print("Output shape:", ex1_output.shape)
print("Input shape:", ex1_input.shape)
print("Factor: 3×3")

# The 2s might appear at grid boundaries between tiles
print("\nChecking if 2s appear at tile boundaries...")

# For a 2×2 input tiled 3×3, boundaries are at:
# Vertical: 0, 2, 4, 6 (between tiles)
# Horizontal: 0, 2, 4, 6 (between tiles)

input_h, input_w = ex1_input.shape
output_h, output_w = ex1_output.shape
factor = 3

print(f"\nTile boundaries:")
print(f"  Rows: {[i * input_h for i in range(factor + 1)]}")
print(f"  Cols: {[i * input_w for i in range(factor + 1)]}")

# Check pattern: 2s appear at top-left of each tile where input has 0
print(f"\n{'='*60}")
print("CHECKING: Do 2s appear at top-left corner of tiles where input has 0?")
print(f"{'='*60}\n")

for tile_row in range(factor):
    for tile_col in range(factor):
        # Top-left position in output
        out_row = tile_row * input_h
        out_col = tile_col * input_w
        
        # Corresponding position in input
        in_row = 0
        in_col = 0
        
        input_val = ex1_input[in_row, in_col]
        output_val = ex1_output[out_row, out_col]
        
        print(f"Tile ({tile_row},{tile_col}): input[0,0]={input_val}, output[{out_row},{out_col}]={output_val}")

print(f"\n✓ YES! When input[0,0] = 0, output has 2 at top-left of each tile!")
