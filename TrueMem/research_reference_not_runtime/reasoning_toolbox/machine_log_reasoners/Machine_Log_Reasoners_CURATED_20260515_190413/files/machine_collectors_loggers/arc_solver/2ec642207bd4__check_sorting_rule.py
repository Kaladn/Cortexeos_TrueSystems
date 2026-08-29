"""
Check if 0d3d703e is about sorting/ordering colors.
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

task = load_task("0d3d703e")

print("HYPOTHESIS: Sorting/Ordering Rule")
print("=" * 60)
print()

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    in_row = inp[0]
    out_row = out[0]
    
    # Sort inputs and see if outputs follow sorted order
    in_sorted = sorted(in_row)
    out_sorted = sorted(out_row)
    
    print(f"Example {i}:")
    print(f"  Input:        {in_row.tolist()}")
    print(f"  Output:       {out_row.tolist()}")
    print(f"  Input sorted: {in_sorted}")
    print(f"  Output sorted: {out_sorted}")
    
    # Check mapping based on position in sorted order
    in_to_rank = {val: rank for rank, val in enumerate(sorted(in_row))}
    out_to_rank = {val: rank for rank, val in enumerate(sorted(out_row))}
    
    print(f"  Input ranks:  {[in_to_rank[v] for v in in_row]}")
    print(f"  Output ranks: {[out_to_rank[v] for v in out_row]}")
    
    # Map by rank position
    sorted_in = sorted(in_row)
    sorted_out = sorted(out_row)
    
    print(f"  Mapping by rank:")
    for rank in range(3):
        print(f"    Rank {rank} (position {rank}): {sorted_in[rank]} → {sorted_out[rank]}")
    
    print()

print("=" * 60)
print("KEY OBSERVATION:")
print("Do inputs map to outputs based on their SORTED POSITION?")
print()

# Check if there's a consistent mapping based on sorted position
print("Checking if mapping is positional (by column in original grid):")
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"Example {i}:")
    for col in range(3):
        in_color = inp[0, col]
        out_color = out[0, col]
        
        # Where does in_color rank?
        in_row = inp[0]
        in_rank = sorted(in_row).index(in_color)
        
        out_row = out[0]
        out_rank = sorted(out_row).index(out_color)
        
        print(f"  Col {col}: in={in_color} (rank {in_rank}) → out={out_color} (rank {out_rank})")
    print()
