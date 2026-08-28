"""Test exhaustive composition search on a single known-solvable task."""

import json
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.arc_operators import OPERATORS

# Load challenges
data_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
with open(data_path) as f:
    challenges = json.load(f)

# Test on 5751f35e - was found as composition in previous tests
task_id = "5751f35e"
task = challenges[task_id]

train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) for ex in task["train"]]

print(f"Testing task {task_id}")
print(f"Train examples: {len(train_pairs)}")
print(f"Input shape: {train_pairs[0][0].shape}")
print(f"Output shape: {train_pairs[0][1].shape}")
print()

# Try ALL operator pairs
compositions_found = []
total_tried = 0

for i, op1 in enumerate(OPERATORS):
    for j, op2 in enumerate(OPERATORS):
        if op1 == op2:
            continue
        
        total_tried += 1
        
        try:
            # Get op1 config
            inp0, out0 = train_pairs[0]
            cfg1 = op1.analyze(inp0, out0)
            if cfg1 is None:
                continue
            
            # Apply op1
            int0 = op1.apply(inp0, cfg1)
            
            # Skip if solved already
            if np.array_equal(int0, out0):
                continue
            
            # Get op2 config
            cfg2 = op2.analyze(int0, out0)
            if cfg2 is None:
                continue
            
            # Validate on all examples
            valid = True
            for inp, out in train_pairs:
                intermediate = op1.apply(inp, cfg1)
                final = op2.apply(intermediate, cfg2)
                if not np.array_equal(final, out):
                    valid = False
                    break
            
            if valid:
                print(f"FOUND: {op1.name} -> {op2.name}")
                compositions_found.append((op1.name, op2.name))
        
        except Exception as e:
            pass

print()
print(f"Tried {total_tried} pairs")
print(f"Found {len(compositions_found)} compositions:")
for c in compositions_found:
    print(f"  {c[0]} -> {c[1]}")
