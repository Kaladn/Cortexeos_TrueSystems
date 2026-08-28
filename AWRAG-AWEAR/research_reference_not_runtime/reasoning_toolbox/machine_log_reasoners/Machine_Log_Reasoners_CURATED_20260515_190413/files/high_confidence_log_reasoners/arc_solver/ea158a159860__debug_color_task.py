"""Debug COLOR-ENGINE on specific task"""

import json
import numpy as np
from engines.color_engine import ColorEngine
from engines.base_engine import TaskView


# Load task 009d5c81
with open("arc-prize-2025/arc-agi_training_challenges.json") as f:
    challenges = json.load(f)

task_id = "009d5c81"
task_data = challenges[task_id]

# Parse
train_pairs = []
for example in task_data['train']:
    input_grid = np.array(example['input'])
    output_grid = np.array(example['output'])
    train_pairs.append((input_grid, output_grid))
    print(f"Train pair: {input_grid.shape} → {output_grid.shape}")
    print(f"  Input colors: {set(input_grid.flatten())}")
    print(f"  Output colors: {set(output_grid.flatten())}")

test_input = np.array(task_data['test'][0]['input'])

task_view = TaskView(
    train_pairs=train_pairs,
    test_input=test_input,
    task_id=task_id,
    metadata={}
)

# Test COLOR-ENGINE
color_engine = ColorEngine()
hypotheses = color_engine.analyze(task_view)

print(f"\nHypotheses: {len(hypotheses)}")
for h in hypotheses:
    print(f"  {h.dsl_program} (conf={h.confidence:.2f})")
    print(f"    {h.explanation}")

if not hypotheses:
    print("\nDEBUG: Why no mapping detected?")
    
    # Check ALL pairs for consistent mapping
    all_mappings = []
    for pair_idx, (inp, out) in enumerate(train_pairs):
        if inp.shape != out.shape:
            print(f"  Pair {pair_idx+1}: Shape mismatch!")
            continue
        
        mapping = {}
        for i in range(inp.shape[0]):
            for j in range(inp.shape[1]):
                in_c = int(inp[i, j])
                out_c = int(out[i, j])
                if in_c not in mapping:
                    mapping[in_c] = out_c
                elif mapping[in_c] != out_c:
                    mapping = None  # Conflict
                    break
            if mapping is None:
                break
        
        if mapping:
            all_mappings.append(mapping)
            print(f"  Pair {pair_idx+1}: {mapping}")
        else:
            print(f"  Pair {pair_idx+1}: INCONSISTENT within pair")
    
    # Check if all pairs have SAME mapping
    if len(all_mappings) == len(train_pairs):
        if all(m == all_mappings[0] for m in all_mappings):
            print(f"\n✓ All pairs have SAME mapping: {all_mappings[0]}")
        else:
            print(f"\n✗ Mappings DIFFER across pairs:")
            for idx, m in enumerate(all_mappings):
                print(f"    Pair {idx+1}: {m}")
