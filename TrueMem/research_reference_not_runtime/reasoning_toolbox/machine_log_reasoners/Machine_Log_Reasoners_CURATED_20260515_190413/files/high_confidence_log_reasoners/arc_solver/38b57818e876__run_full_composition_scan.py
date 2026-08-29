"""
FULL COMPOSITION SCAN — Phase 2 Complete Evaluation

Runs composition engine on entire ARC training + evaluation dataset.
Compares results against baseline to measure gains from composition.
"""

import json
import numpy as np
import sys
import time
from datetime import datetime

# Force UTF-8 encoding for Windows PowerShell
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.composition_engine import CompositionSearch
from cod_616.arc_organ.arc_operators import OPERATORS, infer_rule_for_task

print("=" * 80)
print("PHASE 2 — FULL COMPOSITION ENGINE SCAN")
print("=" * 80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Load datasets
train_dataset_path = "arc-prize-2025/arc-agi_training_challenges.json"
eval_dataset_path = "arc-prize-2025/arc-agi_evaluation_challenges.json"
baseline_path = "solutions_with_new_operators.json"

print("Loading datasets...")
with open(train_dataset_path, 'r') as f:
    train_tasks = json.load(f)
with open(eval_dataset_path, 'r') as f:
    eval_tasks = json.load(f)

all_tasks = {**train_tasks, **eval_tasks}
print(f"  Training: {len(train_tasks)} tasks")
print(f"  Evaluation: {len(eval_tasks)} tasks")
print(f"  Total: {len(all_tasks)} tasks")
print()

# Load baseline
with open(baseline_path, 'r') as f:
    baseline = json.load(f)
print(f"Baseline solves: {len(baseline)} tasks")
print()

# Initialize composition search
print(f"Initializing composition engine...")
search = CompositionSearch(OPERATORS)
print(f"  Operators: {len(OPERATORS)}")
print(f"  Possible 2-step chains: {len(OPERATORS) ** 2}")
print()

# Results tracking
results = {
    "timestamp": datetime.now().isoformat(),
    "total_tasks": len(all_tasks),
    "baseline_solves": len(baseline),
    "solved_composition": {},
    "solved_single": {},
    "failed": [],
    "task_times": {}
}

# Run full scan
print("=" * 80)
print("STARTING FULL SCAN")
print("=" * 80)
print()

start_time = time.time()
task_ids = sorted(all_tasks.keys())

for i, task_id in enumerate(task_ids):
    task = all_tasks[task_id]
    task_start = time.time()
    
    # Progress indicator
    if (i + 1) % 50 == 0:
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed
        remaining = (len(task_ids) - i - 1) / rate
        print(f"[{i+1}/{len(task_ids)}] {elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")
    
    # Use the GOLD STANDARD pipeline: baseline first, composition second
    try:
        # STEP 1: Try baseline single-operator solver (56 solves guaranteed)
        train_pairs = [(np.array(p["input"]), np.array(p["output"])) for p in task["train"]]
        op, config = infer_rule_for_task(train_pairs)
        
        if op is not None and config is not None:
            # Baseline solved it
            results["solved_single"][task_id] = {
                "operator": op.name,
                "config": str(config)
            }
            results["task_times"][task_id] = time.time() - task_start
            found = True
        else:
            # STEP 2: Baseline failed, try composition
            composition_result = search.find_best_2_step(task, prior_ranked=None)
            
            if composition_result:
                op1, op2, cfg1, cfg2 = composition_result
                results["solved_composition"][task_id] = {
                    "operators": [op1.name, op2.name],
                    "configs": {op1.name: str(cfg1), op2.name: str(cfg2)}
                }
                results["task_times"][task_id] = time.time() - task_start
                found = True
            else:
                # Nothing worked
                results["failed"].append(task_id)
                results["task_times"][task_id] = time.time() - task_start
                found = False
                
    except Exception as e:
        # Handle any errors
        results["failed"].append(task_id)
        results["task_times"][task_id] = time.time() - task_start
        found = False

total_time = time.time() - start_time

print()
print("=" * 80)
print("SCAN COMPLETE")
print("=" * 80)
print()

# Calculate metrics
solved_composition = len(results["solved_composition"])
solved_single = len(results["solved_single"])
total_solved = solved_composition + solved_single
failed = len(results["failed"])

baseline_set = set(baseline.keys())
composition_set = set(results["solved_composition"].keys())
single_set = set(results["solved_single"].keys())
all_solved_set = composition_set | single_set

new_solves = all_solved_set - baseline_set
lost_solves = baseline_set - all_solved_set
maintained = baseline_set & all_solved_set

print(f"RESULTS SUMMARY:")
print(f"  Total tasks: {len(all_tasks)}")
print(f"  Solved by composition: {solved_composition} ({solved_composition/len(all_tasks)*100:.2f}%)")
print(f"  Solved by single op: {solved_single} ({solved_single/len(all_tasks)*100:.2f}%)")
print(f"  Total solved: {total_solved} ({total_solved/len(all_tasks)*100:.2f}%)")
print(f"  Failed: {failed} ({failed/len(all_tasks)*100:.2f}%)")
print()

print(f"COMPARISON TO BASELINE:")
print(f"  Baseline: {len(baseline)} solves")
print(f"  New engine: {total_solved} solves")
print(f"  Gain: {len(new_solves)} tasks ({'+' if len(new_solves) > 0 else ''}{len(new_solves)})")
print(f"  Lost: {len(lost_solves)} tasks")
print(f"  Maintained: {len(maintained)} tasks")
print(f"  Net change: {total_solved - len(baseline)} ({'+' if total_solved >= len(baseline) else ''}{total_solved - len(baseline)})")
print()

print(f"PERFORMANCE:")
print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f}min)")
print(f"  Avg time per task: {total_time/len(all_tasks):.2f}s")
print()

# Show new solves
if new_solves:
    print(f"NEW SOLVES ({len(new_solves)} tasks):")
    for task_id in sorted(new_solves)[:20]:
        if task_id in composition_set:
            ops = results["solved_composition"][task_id]["operators"]
            print(f"  + {task_id}: {' -> '.join(ops)}")
        else:
            op = results["solved_single"][task_id]["operator"]
            print(f"  + {task_id}: {op}")
    if len(new_solves) > 20:
        print(f"  ... and {len(new_solves) - 20} more")
    print()

# Show lost solves
if lost_solves:
    print(f"LOST SOLVES ({len(lost_solves)} tasks - REGRESSIONS):")
    for task_id in sorted(lost_solves)[:15]:
        baseline_op = baseline[task_id].get("operator", "unknown")
        print(f"  - {task_id} (was: {baseline_op})")
    if len(lost_solves) > 15:
        print(f"  ... and {len(lost_solves) - 15} more")
    print()

# Save results
output_path = "composition_full_scan_results.json"
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print("=" * 80)
print(f"Results saved to {output_path}")
print("=" * 80)
print()

# Final assessment
if total_solved > len(baseline):
    gain = total_solved - len(baseline)
    print(f"SUCCESS! Gained {gain} tasks with composition engine!")
    print(f"   {len(baseline)} -> {total_solved} tasks ({len(baseline)/1000*100:.1f}% -> {total_solved/1000*100:.1f}%)")
elif total_solved == len(baseline):
    print(f"OK: Maintained baseline ({total_solved} tasks)")
    print(f"  Found {solved_composition} multi-step compositions")
else:
    loss = len(baseline) - total_solved
    print(f"WARNING: Net loss of {loss} tasks (regressions to investigate)")
    print(f"  But discovered {solved_composition} new composition patterns")

print()
print("=" * 80)
print("PHASE 2 COMPLETE")
print("=" * 80)
