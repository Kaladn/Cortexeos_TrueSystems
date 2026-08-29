"""
Analyze positional recoloring pattern in 05269061.

The output shows: color depends on (row, col) position.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np

def load_task(task_id: str) -> dict:
    train_path = "arc-prize-2025/arc-agi_training_challenges.json"
    with open(train_path, 'r') as f:
        data = json.load(f)
    return data[task_id]

task = load_task("05269061")

print("ANALYZING POSITIONAL RECOLORING: 05269061")
print("=" * 60)

ex = task['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])

print("\nExample 1:")
print(f"Input:\n{inp}")
print(f"\nOutput:\n{out}")
print()

# Analyze output pattern
print("Output pattern analysis:")
print(f"  Row 0: {out[0].tolist()}")
print(f"  Row 1: {out[1].tolist()}")
print(f"  Row 2: {out[2].tolist()}")
print()

# Check if output is periodic
print("Checking periodicity:")
for period in [1, 2, 3, 4, 5]:
    periodic = True
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            # Check if it repeats with this period
            if j >= period:
                if out[i, j] != out[i, j % period]:
                    periodic = False
                    break
        if not periodic:
            break
    
    if periodic:
        print(f"  Column period: {period}")
        break

# Check row periodicity
for period in [1, 2, 3, 4, 5]:
    periodic = True
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            if i >= period:
                if out[i, j] != out[i % period, j]:
                    periodic = False
                    break
        if not periodic:
            break
    
    if periodic:
        print(f"  Row period: {period}")
        break

print()
print("Pattern observation:")
print("  Output appears to be a TILING pattern!")
print("  The input has a small pattern in corner: [[2,8,3], [8,3,0], [3,0,0]]")
print("  The output tiles/extends this pattern across the grid")
print()

# Extract the non-zero pattern from input
print("Non-background pattern in input:")
non_zero_positions = []
for i in range(inp.shape[0]):
    for j in range(inp.shape[1]):
        if inp[i, j] != 0:
            non_zero_positions.append((i, j, inp[i, j]))
            print(f"  ({i},{j}): {inp[i, j]}")

print()
print("Hypothesis: The non-zero input defines a tile that gets repeated!")
print("  Input corner pattern → tiled/striped across output")
print("  Background (0) gets filled with periodic pattern")
print()

# Check if output follows diagonal stripes
print("Checking diagonal pattern:")
for i in range(min(out.shape[0], 3)):
    for j in range(min(out.shape[1], 3)):
        pos_sum = (i + j) % 3
        print(f"  ({i},{j}): color={out[i,j]}, (i+j)%3={pos_sum}")
