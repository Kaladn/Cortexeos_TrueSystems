"""
Evaluate MetaCompEngine on full ARC 2025 training set.

Tests:
1. Macro execution (57 Math-DSL rules)
2. Single operators (20 expected)
3. 2-step composition (1 expected)
4. 3-step composition (NEW - targeting +10-30)

TARGET: 70-100 solves (7-10% coverage)
"""

import json
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.arc_operators import OPERATORS
from arc_organ.feature_extractor import FeatureExtractor
from arc_organ.mixer import PriorRanker
from arc_organ.meta_comp_engine import MetaCompEngine


def evaluate_meta_comp():
    """Run MetaCompEngine on all 1000 training tasks."""
    print("="*70)
    print("META-COMP-ENGINE EVALUATION")
    print("="*70)
    print()
    
    # Load data
    data_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
    with open(data_path) as f:
        challenges = json.load(f)
    print(f"[OK] Loaded {len(challenges)} tasks")
    print()
    
    # Initialize engine
    feature_db_path = Path(__file__).parent.parent / "training_feature_database.json"
    math_dsl_path = Path(__file__).parent.parent / "arc_transformation_rules_math_dsl.jsonl"
    
    prior_ranker = PriorRanker(feature_db_path) if feature_db_path.exists() else None
    engine = MetaCompEngine(OPERATORS, prior_ranker, math_dsl_path)
    extractor = FeatureExtractor()
    print()
    
    # Results storage
    results = {
        "macro_solves": [],
        "single_solves": [],
        "composition_2step": [],
        "composition_3step": [],
        "failed": [],
        "solve_details": {}
    }
    
    # Try to load existing results
    results_path = Path(__file__).parent.parent / "meta_comp_results.json"
    if results_path.exists():
        print("[OK] Loading existing results...")
        with open(results_path) as f:
            results = json.load(f)
        print(f"[OK] Resuming from {len(results['solve_details'])} tasks")
        print()
    
    # Evaluate
    start_time = time.time()
    
    for idx, task_id in enumerate(challenges.keys(), 1):
        # Skip if already evaluated
        if task_id in results["solve_details"]:
            continue
        
        task = challenges[task_id]
        features = extractor.extract(task)
        
        # Try to solve (without 3-step for now - too slow)
        result = engine.solve_task(task_id, task, features, try_3step=False)
        
        # Record result
        if result:
            result_type = result["type"]
            
            if result_type == "macro":
                results["macro_solves"].append(task_id)
                print(f"[{idx:4d}/1000] [MACRO] {task_id}: {' -> '.join(result['operators'])}")
            elif result_type == "single":
                results["single_solves"].append(task_id)
                print(f"[{idx:4d}/1000] [SINGLE] {task_id}: {result['operators'][0]}")
            elif result_type == "composition":
                results["composition_2step"].append(task_id)
                print(f"[{idx:4d}/1000] [2-STEP] {task_id}: {' -> '.join(result['operators'])}")
            elif result_type == "composition_3step":
                results["composition_3step"].append(task_id)
                print(f"[{idx:4d}/1000] [3-STEP] {task_id}: {' -> '.join(result['operators'])}")
            
            results["solve_details"][task_id] = {
                "type": result_type,
                "operators": result["operators"]
            }
        else:
            results["failed"].append(task_id)
            if idx % 50 == 0:
                print(f"[{idx:4d}/1000] [FAILED] {task_id}")
        
        # Save progress every 100 tasks
        if idx % 100 == 0:
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)
            
            total_solves = (len(results["macro_solves"]) + len(results["single_solves"]) + 
                          len(results["composition_2step"]) + len(results["composition_3step"]))
            
            elapsed = time.time() - start_time
            rate = idx / elapsed
            remaining = (1000 - idx) / rate
            
            print()
            print(f"Progress: {idx}/1000 tasks ({idx/10:.1f}%)")
            print(f"Solves: {len(results['macro_solves'])} macro + {len(results['single_solves'])} single + "
                  f"{len(results['composition_2step'])} 2-step + {len(results['composition_3step'])} 3-step = {total_solves} total")
            print(f"Rate: {rate:.1f} tasks/sec | ETA: {remaining/60:.1f} min")
            print()
    
    # Final save
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    total_solves = (len(results["macro_solves"]) + len(results["single_solves"]) + 
                   len(results["composition_2step"]) + len(results["composition_3step"]))
    
    print()
    print("="*70)
    print("FINAL RESULTS")
    print("="*70)
    print(f"Macro solves:            {len(results['macro_solves']):4d} ({len(results['macro_solves'])/10:.1f}%)")
    print(f"Single operator solves:  {len(results['single_solves']):4d} ({len(results['single_solves'])/10:.1f}%)")
    print(f"2-step composition:      {len(results['composition_2step']):4d} ({len(results['composition_2step'])/10:.1f}%)")
    print(f"3-step composition:      {len(results['composition_3step']):4d} ({len(results['composition_3step'])/10:.1f}%)")
    print(f"Total solves:            {total_solves:4d} ({total_solves/10:.1f}%)")
    print(f"Failed:                  {len(results['failed']):4d} ({len(results['failed'])/10:.1f}%)")
    print()
    
    # Show breakdown
    if results["macro_solves"]:
        print("MACRO SOLUTIONS:")
        for task_id in results["macro_solves"][:10]:
            ops = results["solve_details"][task_id]["operators"]
            print(f"  {task_id}: {' -> '.join(ops)}")
        if len(results["macro_solves"]) > 10:
            print(f"  ... and {len(results['macro_solves']) - 10} more")
        print()
    
    if results["composition_2step"]:
        print("2-STEP COMPOSITIONS:")
        for task_id in results["composition_2step"]:
            ops = results["solve_details"][task_id]["operators"]
            print(f"  {task_id}: {' -> '.join(ops)}")
        print()
    
    if results["composition_3step"]:
        print("3-STEP COMPOSITIONS:")
        for task_id in results["composition_3step"]:
            ops = results["solve_details"][task_id]["operators"]
            print(f"  {task_id}: {' -> '.join(ops)}")
        print()
    
    print(f"Results saved to: {results_path}")
    print()
    
    elapsed = time.time() - start_time
    print(f"Total time: {elapsed/60:.1f} minutes ({elapsed/1000:.2f} sec/task)")


if __name__ == "__main__":
    evaluate_meta_comp()
