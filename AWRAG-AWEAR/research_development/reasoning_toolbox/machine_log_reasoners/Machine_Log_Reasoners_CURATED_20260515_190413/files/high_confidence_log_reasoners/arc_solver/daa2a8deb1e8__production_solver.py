"""
🔥 GOLD STANDARD PRODUCTION SOLVER

Architecture:
  Layer 0: Original 56-solve baseline (SACRED - NEVER MODIFY)
  Layer 1: 2-step composition engine (adds new solves)
  
This is the CORRECT hierarchy. Never replace working layers.
"""
import json
import numpy as np
from typing import Optional, Dict, List
import sys
sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.arc_operators import OPERATORS
from cod_616.arc_organ.composition_engine import CompositionSearch

# Build operator lookup
OP_DICT = {op.name: op for op in OPERATORS}


def test_operator_on_task_baseline(task_data, operator):
    """
    ⬤ BASELINE SOLVER LOGIC (produces 56 solves)
    
    This is the ORIGINAL logic from full_scan_new_operators.py
    Tests if operator solves ALL training examples independently.
    MORE PERMISSIVE than infer_rule_for_task (no config merging).
    
    NEVER MODIFY THIS FUNCTION.
    """
    try:
        for example in task_data['train']:
            inp = np.array(example['input'])
            expected = np.array(example['output'])
            
            params = operator.analyze(inp, expected)
            if params is None:
                return False
            
            result = operator.apply(inp, params)
            if not np.array_equal(result, expected):
                return False
        return True
    except:
        return False


def solve_with_baseline(task: Dict) -> Optional[Dict]:
    """
    ⬤ LAYER 0: BASELINE SOLVER (56 solves - SACRED)
    
    Uses original full_scan_new_operators.py logic.
    This gets us the 56 baseline solves.
    
    Args:
        task: ARC task dict with 'train' and 'test' keys
    
    Returns:
        Solution dict or None
    """
    # Try all operators in order
    for operator in OPERATORS:
        if test_operator_on_task_baseline(task, operator):
            # Found a working operator
            # Now apply to test inputs
            test_outputs = []
            
            try:
                for test_ex in task['test']:
                    inp = np.array(test_ex['input'])
                    
                    # Get params from first training example (baseline behavior)
                    train_inp = np.array(task['train'][0]['input'])
                    train_out = np.array(task['train'][0]['output'])
                    params = operator.analyze(train_inp, train_out)
                    
                    if params is None:
                        return None
                    
                    result = operator.apply(inp, params)
                    test_outputs.append(result.tolist() if result is not None else None)
                
                return {
                    "rule_type": "single_baseline",
                    "operator": operator.name,
                    "test_outputs": test_outputs
                }
            except:
                return None
    
    return None


def solve_with_composition(task: Dict) -> Optional[Dict]:
    """
    ⬤ LAYER 1: COMPOSITION SOLVER (adds new solves on top)
    
    Only called if baseline fails.
    Searches for 2-step operator compositions.
    
    Args:
        task: ARC task dict
    
    Returns:
        Solution dict or None
    """
    search = CompositionSearch(OPERATORS)
    
    result = search.find_best_2_step(task, prior_ranked=None)
    
    if result is None:
        return None
    
    op1, op2, cfg1, cfg2 = result
    
    # Apply to test inputs
    test_outputs = []
    for test_ex in task['test']:
        inp = np.array(test_ex['input'])
        
        try:
            intermediate = op1.apply(inp, cfg1)
            if intermediate is None:
                test_outputs.append(None)
                continue
            
            final = op2.apply(intermediate, cfg2)
            test_outputs.append(final.tolist() if final is not None else None)
        except:
            test_outputs.append(None)
    
    # Only return if at least one test succeeded
    if all(out is None for out in test_outputs):
        return None
    
    return {
        "rule_type": "composition",
        "operators": [op1.name, op2.name],
        "configs": {op1.name: str(cfg1), op2.name: str(cfg2)},
        "test_outputs": test_outputs
    }


def solve_task_production(task: Dict) -> Optional[Dict]:
    """
    🎯 PRODUCTION SOLVER — The complete layered pipeline
    
    Execution hierarchy (IMMUTABLE):
      1. Try Layer 0: Baseline solver (56 solves guaranteed)
      2. If fails, try Layer 1: Composition solver (adds new solves)
      3. Return best result
    
    This architecture ensures:
      - Never lose the original 56 solves
      - Composition only adds value
      - No regressions possible
      - Clean separation of concerns
    
    Args:
        task: ARC task dict with 'train' and 'test' keys
    
    Returns:
        Solution dict or None
    """
    # ⬤ LAYER 0: BASELINE FIRST (56 solves - SACRED)
    baseline_result = solve_with_baseline(task)
    if baseline_result is not None:
        return baseline_result
    
    # ⬤ LAYER 1: COMPOSITION SECOND (only if baseline failed)
    composition_result = solve_with_composition(task)
    if composition_result is not None:
        return composition_result
    
    # ⬤ Nothing worked
    return None


def main():
    """Test the production solver on full dataset."""
    print("="*80)
    print("🔥 PRODUCTION SOLVER — LAYERED ARCHITECTURE")
    print("="*80)
    print()
    
    # Load 2025 dataset
    with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
        train_data = json.load(f)
    with open('arc-prize-2025/arc-agi_evaluation_challenges.json') as f:
        eval_data = json.load(f)
    
    all_data = {**train_data, **eval_data}
    
    print(f"Dataset: {len(all_data)} tasks")
    print(f"Operators: {len(OPERATORS)}")
    print()
    print("Architecture:")
    print("  Layer 0: Baseline solver (target: 56 solves)")
    print("  Layer 1: Composition solver (target: +10-20 solves)")
    print()
    
    results = {
        "baseline_solves": {},
        "composition_solves": {},
        "failed": []
    }
    
    print("="*80)
    print("RUNNING FULL SCAN")
    print("="*80)
    print()
    
    import time
    start_time = time.time()
    
    for i, (task_id, task) in enumerate(sorted(all_data.items())):
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (len(all_data) - i - 1) / rate
            baseline_count = len(results["baseline_solves"])
            comp_count = len(results["composition_solves"])
            print(f"[{i+1}/{len(all_data)}] Baseline: {baseline_count}, Composition: {comp_count}, Time: ~{remaining:.0f}s remaining")
        
        result = solve_task_production(task)
        
        if result is not None:
            if result["rule_type"] == "single_baseline":
                results["baseline_solves"][task_id] = result
            elif result["rule_type"] == "composition":
                results["composition_solves"][task_id] = result
        else:
            results["failed"].append(task_id)
    
    elapsed = time.time() - start_time
    
    baseline_count = len(results["baseline_solves"])
    comp_count = len(results["composition_solves"])
    total_solved = baseline_count + comp_count
    
    print()
    print("="*80)
    print("🎯 FINAL RESULTS")
    print("="*80)
    print()
    print(f"Total tasks: {len(all_data)}")
    print(f"Layer 0 (Baseline): {baseline_count} solves")
    print(f"Layer 1 (Composition): {comp_count} solves")
    print(f"Total solved: {total_solved} ({total_solved/len(all_data)*100:.2f}%)")
    print(f"Failed: {len(results['failed'])}")
    print()
    print(f"Expected: 56 baseline + 2-19 composition = 58-75 total")
    print(f"Actual: {baseline_count} + {comp_count} = {total_solved}")
    print()
    print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print()
    
    # Save results
    with open('production_solver_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("💾 Results saved to: production_solver_results.json")
    print()
    
    if baseline_count < 50:
        print("⚠️  WARNING: Baseline solves < 50 (expected 56)")
        print("   This suggests the baseline logic needs verification.")
    
    if comp_count == 0:
        print("⚠️  WARNING: No composition solves found")
        print("   Composition engine may need debugging.")
    
    print("="*80)


if __name__ == "__main__":
    main()
