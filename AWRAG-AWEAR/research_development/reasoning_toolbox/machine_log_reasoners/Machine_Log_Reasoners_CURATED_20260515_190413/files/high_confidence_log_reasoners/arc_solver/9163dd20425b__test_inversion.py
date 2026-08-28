"""Check if 0d3d703e uses rank INVERSION (smallest→largest, largest→smallest)."""
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

print("TESTING RANK INVERSION HYPOTHESIS")
print("=" * 60)
print()

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    in_row = inp[0]
    out_row = out[0]
    
    # Sort colors
    in_sorted = sorted(in_row)
    out_sorted = sorted(out_row)
    
    print(f"Example {i}:")
    print(f"  Input:  {in_row.tolist()}")
    print(f"  Output: {out_row.tolist()}")
    print(f"  Input sorted:  {in_sorted}")
    print(f"  Output sorted: {out_sorted}")
    print()
    
    # Test INVERSION: smallest input → largest output
    print(f"  Testing INVERSION (smallest→largest):")
    inverted_mapping = {}
    for j in range(3):
        inverted_mapping[in_sorted[j]] = out_sorted[-(j+1)]  # Reverse index
        print(f"    {in_sorted[j]} (rank {j}) → {out_sorted[-(j+1)]} (rank {2-j})")
    
    print(f"  Inverted mapping: {inverted_mapping}")
    
    # Apply and check
    predicted = np.array(in_row)
    for k in range(len(predicted)):
        predicted[k] = inverted_mapping.get(predicted[k], predicted[k])
    
    print(f"  Predicted: {predicted.tolist()}")
    print(f"  Actual:    {out_row.tolist()}")
    print(f"  MATCH: {np.array_equal(predicted, out_row)} {'✓' if np.array_equal(predicted, out_row) else '✗'}")
    print()

print("=" * 60)
