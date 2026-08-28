"""
Quick composition test on known solvable tasks.
Tests the 2-step chain logic before full dataset scan.
"""

import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.composition_engine import CompositionSearch
from cod_616.arc_organ.prior_selector import PriorSelector
from cod_616.arc_organ.arc_operators import OPERATORS

print("=" * 80)
print("COMPOSITION ENGINE — QUICK VALIDATION TEST")
print("=" * 80)
print()

# Load a few training tasks
dataset_path = "arc-prize-2025/arc-agi_training_challenges.json"

try:
    with open(dataset_path, 'r') as f:
        all_tasks = json.load(f)
except FileNotFoundError:
    print(f"Error: Dataset not found at {dataset_path}")
    print("Please adjust path in script")
    sys.exit(1)

# Pick 10 random tasks for quick test
import random
test_task_ids = random.sample(list(all_tasks.keys()), 10)

print(f"Testing composition on {len(test_task_ids)} random tasks...")
print(f"Operators available: {len(OPERATORS)}")
print(f"Possible 2-step chains: {len(OPERATORS) ** 2}")
print()

# Initialize search
search = CompositionSearch(OPERATORS)

results = {
    "solved_composition": [],
    "solved_single": [],
    "failed": []
}

for i, task_id in enumerate(test_task_ids):
    task = all_tasks[task_id]
    
    print(f"[{i+1}/{len(test_task_ids)}] {task_id}...", end=" ", flush=True)
    
    # Try 2-step composition
    composition_result = search.find_best_2_step(task, prior_ranked=None)
    
    if composition_result:
        op1, op2, cfg1, cfg2 = composition_result
        results["solved_composition"].append(task_id)
        print(f"✓ COMPOSITION: {op1.name} → {op2.name}")
        continue
    
    # Try single operators (fallback)
    found_single = False
    for op in OPERATORS:
        try:
            train_ex = task["train"][0]
            config = op.analyze(train_ex["input"], train_ex["output"])
            
            if config is None:
                continue
            
            # Validate on all training examples
            valid = True
            for pair in task["train"]:
                result = op.apply(pair["input"], config)
                if not np.array_equal(result, pair["output"]):
                    valid = False
                    break
            
            if valid:
                results["solved_single"].append(task_id)
                print(f"✓ SINGLE: {op.name}")
                found_single = True
                break
        except Exception:
            continue
    
    if not found_single:
        results["failed"].append(task_id)
        print("✗ FAILED")

print()
print("=" * 80)
print("QUICK TEST RESULTS")
print("=" * 80)
print(f"Solved by composition: {len(results['solved_composition'])}/{len(test_task_ids)}")
print(f"Solved by single op: {len(results['solved_single'])}/{len(test_task_ids)}")
print(f"Total solved: {len(results['solved_composition']) + len(results['solved_single'])}/{len(test_task_ids)}")
print(f"Failed: {len(results['failed'])}/{len(test_task_ids)}")
print()

if results["solved_composition"]:
    print("✅ COMPOSITION ENGINE WORKING!")
    print("Tasks solved by composition:")
    for task_id in results["solved_composition"]:
        print(f"  - {task_id}")
else:
    print("⚠️  No composition solves in this sample (expected — only 10 random tasks)")
    print("This is normal. Composition helps on harder multi-step tasks.")

print()
print("=" * 80)
print("READY FOR FULL SCAN:")
print("  python run_full_composition_scan.py")
print("=" * 80)
