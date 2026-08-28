"""
DSL Auto-Extraction: Extract operator chains from all 1000 training tasks.

This script:
1. Loads all training solutions (from feature database or by brute-force testing)
2. For each solved task, extracts the minimal operator chain
3. Writes to Math-DSL format (JSONL)
4. Target: 57 → 400+ rules for MacroExecutor

This is the FASTEST path to 100+ solves.
"""

import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.arc_operators import OPERATORS
from arc_organ.composition_engine import CompositionSearch


def extract_dsl_from_training():
    """
    Extract DSL rules from all training tasks by:
    1. Trying single operators
    2. Trying 2-step compositions  
    3. Trying 3-step compositions (limited)
    4. Recording successful chains
    """
    print("="*70)
    print("DSL AUTO-EXTRACTION")
    print("="*70)
    print()
    
    # Load training data
    challenges_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
    with open(challenges_path) as f:
        challenges = json.load(f)
    
    print(f"[OK] Loaded {len(challenges)} training tasks")
    print(f"[OK] Testing with {len(OPERATORS)} operators")
    print()
    
    # Load existing DSL rules
    dsl_path = Path(__file__).parent.parent / "arc_transformation_rules_math_dsl.jsonl"
    existing_rules = set()
    if dsl_path.exists():
        with open(dsl_path) as f:
            for line in f:
                if line.strip():
                    rule = json.loads(line)
                    existing_rules.add(rule["task_id"])
    
    print(f"[OK] Found {len(existing_rules)} existing DSL rules")
    print()
    
    # Output path
    output_path = Path(__file__).parent.parent / "arc_transformation_rules_expanded.jsonl"
    
    # Initialize composition search
    comp_search = CompositionSearch(OPERATORS)
    
    # Extract rules
    new_rules = []
    single_op_count = 0
    two_step_count = 0
    three_step_count = 0
    
    for idx, (task_id, task) in enumerate(challenges.items(), 1):
        # Skip if already have rule
        if task_id in existing_rules:
            continue
        
        train_examples = task.get("train", [])
        if not train_examples:
            continue
        
        train_pairs = [(np.array(ex["input"]), np.array(ex["output"])) 
                      for ex in train_examples]
        
        # Try single operators first
        solution = None
        for op in OPERATORS:
            try:
                cfg = op.analyze(train_pairs[0][0], train_pairs[0][1])
                if cfg is None:
                    continue
                
                # Validate on all examples
                valid = True
                for inp, out in train_pairs:
                    result = op.apply(inp, cfg)
                    if not np.array_equal(result, out):
                        valid = False
                        break
                
                if valid:
                    solution = {
                        "task_id": task_id,
                        "operators": [op.name],
                        "chain_length": 1,
                        "rule": f"Single operator: {op.name}"
                    }
                    single_op_count += 1
                    break
            except Exception:
                continue
        
        # Try 2-step if single didn't work
        if solution is None:
            result_2step = comp_search.find_best_2_step(task, None)
            if result_2step:
                op1, op2, cfg1, cfg2 = result_2step
                solution = {
                    "task_id": task_id,
                    "operators": [op1.name, op2.name],
                    "chain_length": 2,
                    "rule": f"2-step composition: {op1.name} -> {op2.name}"
                }
                two_step_count += 1
        
        # Try 3-step if 2-step didn't work (limited search - top 5 ops only)
        if solution is None:
            top_5_ops = OPERATORS[:5]  # Limit to avoid exponential explosion
            for op1 in top_5_ops:
                for op2 in top_5_ops:
                    if op1 == op2:
                        continue
                    for op3 in top_5_ops:
                        if op3 == op1 or op3 == op2:
                            continue
                        
                        try:
                            # Test 3-step chain
                            inp0, out0 = train_pairs[0]
                            cfg1 = op1.analyze(inp0, out0)
                            if cfg1 is None:
                                continue
                            
                            int1 = op1.apply(inp0, cfg1)
                            if np.array_equal(int1, out0):
                                continue  # Already solved
                            
                            cfg2 = op2.analyze(int1, out0)
                            if cfg2 is None:
                                continue
                            
                            int2 = op2.apply(int1, cfg2)
                            if np.array_equal(int2, out0):
                                continue  # Solved in 2 steps
                            
                            cfg3 = op3.analyze(int2, out0)
                            if cfg3 is None:
                                continue
                            
                            # Validate on all examples
                            valid = True
                            for inp, out in train_pairs:
                                step1 = op1.apply(inp, cfg1)
                                step2 = op2.apply(step1, cfg2)
                                step3 = op3.apply(step2, cfg3)
                                if not np.array_equal(step3, out):
                                    valid = False
                                    break
                            
                            if valid:
                                solution = {
                                    "task_id": task_id,
                                    "operators": [op1.name, op2.name, op3.name],
                                    "chain_length": 3,
                                    "rule": f"3-step composition: {op1.name} -> {op2.name} -> {op3.name}"
                                }
                                three_step_count += 1
                                break
                        except Exception:
                            continue
                    
                    if solution:
                        break
                if solution:
                    break
        
        # Record solution
        if solution:
            new_rules.append(solution)
            chain_type = ["SINGLE", "2-STEP", "3-STEP"][solution["chain_length"] - 1]
            print(f"[{idx:4d}/1000] [{chain_type:7s}] {task_id}: {' -> '.join(solution['operators'])}")
        elif idx % 100 == 0:
            print(f"[{idx:4d}/1000] [FAILED] {task_id}")
        
        # Save progress every 100 tasks
        if idx % 100 == 0:
            with open(output_path, "w") as f:
                for rule in new_rules:
                    f.write(json.dumps(rule) + "\n")
            
            total = single_op_count + two_step_count + three_step_count
            print()
            print(f"Progress: {idx}/1000 tasks")
            print(f"Extracted: {single_op_count} single + {two_step_count} 2-step + {three_step_count} 3-step = {total} total")
            print(f"Coverage: {(len(existing_rules) + total)/10:.1f}%")
            print()
    
    # Final save
    with open(output_path, "w") as f:
        for rule in new_rules:
            f.write(json.dumps(rule) + "\n")
    
    # Summary
    total = single_op_count + two_step_count + three_step_count
    total_with_existing = len(existing_rules) + total
    
    print()
    print("="*70)
    print("EXTRACTION COMPLETE")
    print("="*70)
    print(f"Single operators:   {single_op_count:4d}")
    print(f"2-step composition: {two_step_count:4d}")
    print(f"3-step composition: {three_step_count:4d}")
    print(f"Total NEW rules:    {total:4d}")
    print(f"Total with existing: {total_with_existing:4d} ({total_with_existing/10:.1f}%)")
    print()
    print(f"Saved to: {output_path}")
    print()
    print("Next step: Merge with existing DSL and test with MacroExecutor")


if __name__ == "__main__":
    extract_dsl_from_training()
