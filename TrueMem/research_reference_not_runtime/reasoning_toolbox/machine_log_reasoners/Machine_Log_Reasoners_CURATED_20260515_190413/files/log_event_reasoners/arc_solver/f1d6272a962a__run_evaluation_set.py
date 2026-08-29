#!/usr/bin/env python3
"""
Run ARC-CORE on EVALUATION set (not training).
This is the real competition performance test.
"""

import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime

from arc_core import ArcCore


def load_evaluation_set():
    """Load evaluation challenges and solutions."""
    eval_path = Path("arc-prize-2024/arc-agi_evaluation_challenges.json")
    sol_path = Path("arc-prize-2024/arc-agi_evaluation_solutions.json")
    
    with open(eval_path) as f:
        challenges = json.load(f)
    
    with open(sol_path) as f:
        solutions = json.load(f)
    
    return challenges, solutions


def run_evaluation():
    """Run on evaluation set."""
    print("=" * 80)
    print("ARC-CORE EVALUATION SET RUN")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load data
    print("Loading evaluation set...")
    challenges, solutions = load_evaluation_set()
    print(f"  Evaluation tasks: {len(challenges)}\n")
    
    # Initialize solver
    print("Initializing ARC-CORE...")
    arc_core = ArcCore()
    print(f"  Engines: {len(arc_core.engines)}")
    print(f"  Active: {', '.join(arc_core.engines.keys())}\n")
    
    # Run evaluation
    print("=" * 80)
    print("RUNNING EVALUATION")
    print("=" * 80)
    
    solved_count = 0
    by_engine = {}
    results = {}
    
    start_time = time.time()
    
    for idx, (task_id, task_data) in enumerate(challenges.items(), 1):
        try:
            # Solve (note: solve takes task_data first, then task_id)
            trace = arc_core.solve(task_data, task_id)
            
            # Check if solved
            if trace.success and task_id in solutions:
                # Verify against ground truth
                expected = solutions[task_id]
                if len(expected) > 0 and len(trace.solution) > 0:
                    expected_grid = np.array(expected[0])
                    solution_grid = trace.solution[0] if isinstance(trace.solution, list) else trace.solution
                    
                    if np.array_equal(solution_grid, expected_grid):
                        solved_count += 1
                        results[task_id] = {
                            'solved': True,
                            'engine': trace.winning_hypothesis.engine_name if trace.winning_hypothesis else 'unknown',
                            'operation': trace.winning_hypothesis.operation if trace.winning_hypothesis else 'unknown'
                        }
                        
                        # Track by engine
                        engine_name = trace.winning_hypothesis.engine_name if trace.winning_hypothesis else 'unknown'
                        by_engine[engine_name] = by_engine.get(engine_name, 0) + 1
                    else:
                        results[task_id] = {'solved': False, 'reason': 'incorrect_output'}
                else:
                    results[task_id] = {'solved': False, 'reason': 'empty_solution'}
            else:
                results[task_id] = {'solved': False, 'reason': 'no_solution'}
        
        except Exception as e:
            results[task_id] = {'solved': False, 'reason': f'error: {str(e)}'}
        
        # Progress
        if idx % 50 == 0 or idx == len(challenges):
            elapsed = time.time() - start_time
            eta = (elapsed / idx) * (len(challenges) - idx)
            print(f"[{idx}/{len(challenges)}] Solved: {solved_count}, ETA: ~{int(eta)}s")
    
    elapsed = time.time() - start_time
    
    # Results
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    
    print(f"\nResults:")
    print(f"  Total tasks:      {len(challenges)}")
    print(f"  Solved:           {solved_count} ({100*solved_count/len(challenges):.2f}%)")
    print(f"  Failed:           {len(challenges) - solved_count}")
    
    if by_engine:
        print(f"\nSolves by engine:")
        for engine, count in sorted(by_engine.items(), key=lambda x: x[1], reverse=True):
            print(f"  {engine:15} {count:3}")
    
    print(f"\nPerformance:")
    print(f"  Total time:       {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"  Average per task: {elapsed/len(challenges):.3f}s")
    
    # Save results
    output_file = f"results/evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("results").mkdir(exist_ok=True)
    
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'total_tasks': len(challenges),
        'solved': solved_count,
        'solve_rate': solved_count / len(challenges),
        'by_engine': by_engine,
        'elapsed_seconds': elapsed,
        'results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("=" * 80)
    
    return solved_count, len(challenges)


if __name__ == "__main__":
    solved, total = run_evaluation()
    print(f"\n🎯 FINAL SCORE: {solved}/{total} ({100*solved/total:.2f}%)")
