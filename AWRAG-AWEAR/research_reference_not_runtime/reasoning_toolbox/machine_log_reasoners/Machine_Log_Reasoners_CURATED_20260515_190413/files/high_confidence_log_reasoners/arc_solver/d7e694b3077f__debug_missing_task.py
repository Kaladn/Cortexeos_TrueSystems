"""Debug why scan doesn't solve task 009d5c81 which baseline solved with shape_reference_recolor"""
import json
import numpy as np
import sys
sys.path.insert(0, r'C:\Users\mydyi\Desktop\cortexos_kaggle_bfrb_project\cod_616')

from arc_organ.arc_operators import infer_rule_for_task, get_all_operators

# Load task
with open(r'arc-prize-2025\arc-agi_evaluation_challenges.json', 'r') as f:
    eval_tasks = json.load(f)

task_id = "009d5c81"
task = eval_tasks[task_id]

print(f"=== Testing {task_id} ===")
print(f"Training examples: {len(task['train'])}")

# Test with infer_rule_for_task (what scan uses)
print("\n1. Using infer_rule_for_task (scan method):")
train_pairs = [(np.array(p["input"]), np.array(p["output"])) for p in task["train"]]
op, config = infer_rule_for_task(train_pairs)
if op:
    print(f"   FOUND: {op.name}")
    print(f"   Config: {config}")
else:
    print("   NOT FOUND")

# Test shape_reference_recolor specifically
print("\n2. Testing shape_reference_recolor directly:")
ops = get_all_operators()
shape_ref_op = [o for o in ops if o.name == "shape_reference_recolor"][0]

for i, pair in enumerate(train_pairs):
    inp, out = pair
    print(f"\n   Example {i+1}:")
    try:
        config = shape_ref_op.analyze(inp, out)
        if config:
            print(f"      Analyze SUCCESS: {config}")
            result = shape_ref_op.apply(inp, config)
            if result is not None and np.array_equal(result, out):
                print(f"      Apply SUCCESS (matches output)")
            else:
                print(f"      Apply FAILED (doesn't match)")
        else:
            print(f"      Analyze returned None")
    except Exception as e:
        print(f"      ERROR: {e}")

print("\n3. Checking why infer_rule_for_task might skip it:")
print("   Testing all operators on first example...")
inp, out = train_pairs[0]
found_any = []
for op in ops:
    try:
        config = op.analyze(inp, out)
        if config:
            result = op.apply(inp, config)
            if result is not None and np.array_equal(result, out):
                found_any.append((op.name, config))
    except:
        pass

print(f"   Operators that work on example 1: {len(found_any)}")
for name, cfg in found_any[:5]:
    print(f"      - {name}: {cfg}")
