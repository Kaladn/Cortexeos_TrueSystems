"""
Test composition engine on KNOWN SOLVABLE tasks from baseline.
This verifies the engine maintains existing solves and finds new ones.
"""

import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.composition_engine import CompositionSearch
from cod_616.arc_organ.arc_operators import OPERATORS

print("=" * 80)
print("COMPOSITION ENGINE — BASELINE REGRESSION TEST")
print("=" * 80)
print()

# Load baseline solved tasks
baseline_path = "solutions_with_new_operators.json"
train_dataset_path = "arc-prize-2025/arc-agi_training_challenges.json"
eval_dataset_path = "arc-prize-2025/arc-agi_evaluation_challenges.json"

with open(baseline_path, 'r') as f:
    baseline = json.load(f)

# Load both training and evaluation datasets
all_tasks = {}
with open(train_dataset_path, 'r') as f:
    all_tasks.update(json.load(f))
with open(eval_dataset_path, 'r') as f:
    all_tasks.update(json.load(f))

print(f"Baseline solves: {len(baseline)} tasks")
print(f"Testing if composition engine maintains these solves...")
print()

# Test on first 20 baseline tasks
test_task_ids = list(baseline.keys())[:20]

search = CompositionSearch(OPERATORS)

maintained = []
lost = []
upgraded_to_composition = []

for i, task_id in enumerate(test_task_ids):
    task = all_tasks[task_id]
    baseline_op = baseline[task_id].get("operator", "unknown")
    
    print(f"[{i+1}/{len(test_task_ids)}] {task_id} (baseline: {baseline_op})...", end=" ", flush=True)
    
    # Try composition first
    composition_result = search.find_best_2_step(task, prior_ranked=None)
    
    if composition_result:
        op1, op2, cfg1, cfg2 = composition_result
        upgraded_to_composition.append((task_id, f"{op1.name} → {op2.name}"))
        print(f"✓ COMPOSITION: {op1.name} → {op2.name}")
        continue
    
    # Try single operators
    found = False
    for op in OPERATORS:
        try:
            train_ex = task["train"][0]
            inp = np.array(train_ex["input"])
            out = np.array(train_ex["output"])
            config = op.analyze(inp, out)
            
            if config is None:
                continue
            
            # Validate on all examples
            valid = True
            for pair in task["train"]:
                pair_inp = np.array(pair["input"])
                pair_out = np.array(pair["output"])
                result = op.apply(pair_inp, config)
                if not np.array_equal(result, pair_out):
                    valid = False
                    break
            
            if valid:
                maintained.append(task_id)
                print(f"✓ SINGLE: {op.name}")
                found = True
                break
        except Exception:
            continue
    
    if not found:
        lost.append(task_id)
        print(f"✗ LOST (regression)")

print()
print("=" * 80)
print("REGRESSION TEST RESULTS")
print("=" * 80)
print(f"Baseline tasks tested: {len(test_task_ids)}")
print(f"Maintained (single op): {len(maintained)}")
print(f"Upgraded (to composition): {len(upgraded_to_composition)}")
print(f"Lost (regression): {len(lost)}")
print(f"SUCCESS RATE: {(len(maintained) + len(upgraded_to_composition))/len(test_task_ids)*100:.1f}%")
print()

if upgraded_to_composition:
    print("TASKS UPGRADED TO COMPOSITION:")
    for task_id, chain in upgraded_to_composition:
        print(f"  ✓ {task_id}: {chain}")
    print()

if lost:
    print("⚠️  TASKS LOST (need investigation):")
    for task_id in lost:
        print(f"  ✗ {task_id}")
    print()

if len(lost) == 0:
    print("✅ NO REGRESSIONS — Engine maintains all baseline solves!")
    print()

print("=" * 80)
print("NEXT: Run full dataset scan to find NEW solves")
print("  python run_full_composition_scan.py")
print("=" * 80)
