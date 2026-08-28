import json
import numpy as np
from cod_616.arc_organ.arc_operators import SwapMappingOperator

# Load d511f180
with open("arc-prize-2024/arc-agi_training_challenges.json", "r") as f:
    train_data = json.load(f)

task = train_data["d511f180"]
train_examples = task["train"]

print("=" * 70)
print("DEBUGGING d511f180 SWAP MAPPING")
print("=" * 70)

op = SwapMappingOperator()

for i, example in enumerate(train_examples):
    inp = np.array(example["input"])
    out = np.array(example["output"])
    
    print(f"\nExample {i+1}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Output shape: {out.shape}")
    print(f"  Input unique: {np.unique(inp)}")
    print(f"  Output unique: {np.unique(out)}")
    
    # Check what changes
    mask = (inp != out)
    changed_positions = np.sum(mask)
    print(f"  Changed positions: {changed_positions}")
    
    if changed_positions > 0:
        changed_from = inp[mask]
        changed_to = out[mask]
        print(f"  Changed from: {np.unique(changed_from)}")
        print(f"  Changed to: {np.unique(changed_to)}")
    
    # Try analyze
    result = op.analyze(inp, out)
    print(f"  SwapMapping result: {result}")
