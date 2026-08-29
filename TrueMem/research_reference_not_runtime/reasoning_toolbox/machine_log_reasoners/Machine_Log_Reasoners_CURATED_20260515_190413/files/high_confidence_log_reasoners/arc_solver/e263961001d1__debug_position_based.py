"""
Debug why position_based_recolor lost 19 solves.
"""
import json
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.arc_operators import PositionBasedRecolorOperator, infer_rule_for_task

# Load one of the lost tasks
DATA_2025 = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"

with open(DATA_2025) as f:
    all_tasks = json.load(f)

# Test task 05269061 (lost solve - was position_based_recolor)
task_id = "05269061"
task_data = all_tasks[task_id]

print(f"Testing task {task_id}")
print(f"Training examples: {len(task_data['train'])}")
print()

# Convert to format for infer_rule_for_task
train_pairs = [
    (np.array(pair["input"]), np.array(pair["output"]))
    for pair in task_data["train"]
]

# Test with infer_rule_for_task (what baseline used)
print("Using infer_rule_for_task:")
op, params = infer_rule_for_task(train_pairs)

if op is None:
    print("× FAILED - no operator found")
else:
    print(f"✓ Solved with: {op.name}")
    print(f"  Params: {params}")

print()

# Test position_based_recolor directly
print("Testing PositionBasedRecolorOperator directly:")
pbr_op = PositionBasedRecolorOperator()

params_list = []
for i, (inp, out) in enumerate(train_pairs):
    print(f"\n  Example {i+1}:")
    print(f"    Input shape: {inp.shape}")
    print(f"    Output shape: {out.shape}")
    
    params = pbr_op.analyze(inp, out)
    if params is None:
        print(f"    × analyze() returned None")
    else:
        print(f"    ✓ analyze() returned params: k={params['k']}, m={params['m']}")
        print(f"      Pattern: {params['pattern']}")
        params_list.append(params)
        
        # Try apply
        result = pbr_op.apply(inp, params)
        if np.array_equal(result, out):
            print(f"    ✓ apply() produces correct output")
        else:
            print(f"    × apply() produces WRONG output")

# Test merge
if params_list:
    print(f"\n  Testing merge_operator_params with {len(params_list)} params...")
    from arc_organ.arc_operators import merge_operator_params
    merged = merge_operator_params(pbr_op, params_list)
    if merged is None:
        print(f"    × merge_operator_params returned None!")
    else:
        print(f"    ✓ merge_operator_params succeeded")
        print(f"      Merged params: k={merged['k']}, m={merged['m']}")
        
        # Verify merged params work on all examples
        all_ok = True
        for i, (inp, out) in enumerate(train_pairs):
            result = pbr_op.apply(inp, merged)
            if not np.array_equal(result, out):
                print(f"      × Merged params FAIL on example {i+1}")
                all_ok = False
        if all_ok:
            print(f"      ✓ Merged params work on all examples!")
