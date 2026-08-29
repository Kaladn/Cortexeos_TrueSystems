"""
Test composition solver on all 1000 training tasks.

This will show us:
- How many tasks single operators solve (baseline: 20)
- How many 2-step compositions add (target: +36 to reach 56+)
- Total solve rate with composition enabled

Should take ~2-5 minutes for 1000 tasks.
"""
import json
import numpy as np
from pathlib import Path
import time
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.solve_task_composition import solve_task, CompositionSolver

BASE_DIR = Path(__file__).parent.parent
TRAINING_CHALLENGES = BASE_DIR / "arc-prize-2025" / "arc-agi_training_challenges.json"
OUTPUT_FILE = BASE_DIR / "results" / "composition_solver_results.json"


def main():
    print("="*70)
    print("TESTING COMPOSITION SOLVER ON 1000 TRAINING TASKS")
    print("="*70)
    print()
    
    # Load training data
    print("Loading training challenges...")
    with open(TRAINING_CHALLENGES) as f:
        challenges = json.load(f)
    print(f"Loaded {len(challenges)} tasks")
    print()
    
    # Initialize solver
    print("Initializing composition solver...")
    solver = CompositionSolver(
        use_composition=True,
        use_prior=False  # Start without priors, add later
    )
    print()
    
    # Test on all tasks
    results = {
        "single_op_solves": {},
        "composition_solves": {},
        "failed": []
    }
    
    single_count = 0
    composition_count = 0
    start_time = time.time()
    
    print("Testing tasks...")
    print()
    
    for i, (task_id, task_data) in enumerate(challenges.items(), 1):
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(challenges) - i) / rate if rate > 0 else 0
            print(f"  [{i}/1000] single={single_count} composition={composition_count} "
                  f"rate={rate:.1f} tasks/s eta={eta:.0f}s")
        
        # Convert to format solver expects
        task = {
            "train": task_data["train"],
            "test": task_data.get("test", [{"input": task_data["train"][0]["input"]}])
        }
        
        try:
            result = solver.solve(task)
            
            if result is None:
                results["failed"].append(task_id)
            elif result["rule_type"] == "single":
                results["single_op_solves"][task_id] = {
                    "operator": result["operator"]
                }
                single_count += 1
            elif result["rule_type"] == "composition":
                results["composition_solves"][task_id] = {
                    "operators": result["operators"]
                }
                composition_count += 1
        except Exception as e:
            results["failed"].append(task_id)
            if i <= 10:  # Show early errors
                print(f"    Error on {task_id}: {e}")
    
    elapsed = time.time() - start_time
    
    print(f"\n  [1000/1000] completed in {elapsed:.1f}s")
    print()
    
    # Save results
    print(f"Saving results to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    
    results["metadata"] = {
        "total_tasks": len(challenges),
        "single_op_solves": single_count,
        "composition_solves": composition_count,
        "total_solves": single_count + composition_count,
        "failed": len(results["failed"]),
        "solve_rate": f"{(single_count + composition_count) / len(challenges) * 100:.2f}%",
        "elapsed_seconds": elapsed
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("✓ Results saved")
    print()
    
    # Statistics
    print("="*70)
    print("RESULTS")
    print("="*70)
    print(f"Total tasks:           1000")
    print(f"Single operator:       {single_count} ({single_count/10:.1f}%)")
    print(f"2-step composition:    {composition_count} ({composition_count/10:.1f}%)")
    print(f"**TOTAL SOLVES:        {single_count + composition_count} ({(single_count + composition_count)/10:.1f}%)**")
    print(f"Failed:                {len(results['failed'])} ({len(results['failed'])/10:.1f}%)")
    print()
    print(f"Time: {elapsed:.1f}s ({elapsed/len(challenges)*1000:.1f}ms per task)")
    print()
    
    # Compare to baseline
    baseline_target = 56
    current_total = single_count + composition_count
    
    if current_total >= baseline_target:
        print(f"✓ BEAT BASELINE: {current_total} solves vs {baseline_target} target (+{current_total - baseline_target})")
    elif current_total >= baseline_target * 0.9:
        print(f"≈ CLOSE TO BASELINE: {current_total} solves vs {baseline_target} target (-{baseline_target - current_total})")
    else:
        print(f"× BELOW BASELINE: {current_total} solves vs {baseline_target} target (-{baseline_target - current_total})")
    print()
    
    # Show sample compositions if any
    if composition_count > 0:
        print("Sample compositions:")
        for task_id, data in list(results["composition_solves"].items())[:5]:
            ops = data["operators"]
            print(f"  {task_id}: {ops[0]} → {ops[1]}")


if __name__ == "__main__":
    main()
