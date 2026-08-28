"""
Test GEO-ENGINE on real ARC tasks

Find tasks that should be solvable by pure geometry:
- Rotations
- Flips
- Translations
- Scaling
- Transpose

Compare GEO-ENGINE vs current baseline.
"""

import json
import numpy as np
from pathlib import Path
from arc_core import ArcCore


def load_arc_dataset():
    """Load ARC 2025 dataset."""
    dataset_path = Path("arc-prize-2025")
    
    with open(dataset_path / "arc-agi_training_challenges.json") as f:
        train_challenges = json.load(f)
    
    with open(dataset_path / "arc-agi_training_solutions.json") as f:
        train_solutions = json.load(f)
    
    return train_challenges, train_solutions


def test_geo_on_arc_tasks(max_tasks=100):
    """Test GEO-ENGINE on real ARC tasks."""
    
    train_challenges, train_solutions = load_arc_dataset()
    core = ArcCore()
    
    results = {
        'total_tested': 0,
        'geo_solved': 0,
        'geo_tasks': [],
    }
    
    print("=" * 60)
    print("GEO-ENGINE vs ARC-2025 Training Set")
    print("=" * 60)
    print(f"Testing first {max_tasks} tasks...\n")
    
    for task_id in list(train_challenges.keys())[:max_tasks]:
        task_data = train_challenges[task_id]
        
        # Add test example with known solution
        task_data['test'] = [{'input': train_solutions[task_id][0]}]
        
        trace = core.solve(task_data, task_id=task_id)
        results['total_tested'] += 1
        
        if trace.success:
            results['geo_solved'] += 1
            results['geo_tasks'].append({
                'task_id': task_id,
                'method': trace.method,
                'hypothesis': str(trace.winning_hypothesis),
                'dsl': trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else None
            })
            
            print(f"✓ {task_id}: {trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else 'solved'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Tasks tested: {results['total_tested']}")
    print(f"GEO-ENGINE solved: {results['geo_solved']} ({results['geo_solved']/results['total_tested']*100:.1f}%)")
    
    if results['geo_tasks']:
        print(f"\nGEO-ENGINE solutions by operation:")
        
        # Group by operation
        ops = {}
        for task in results['geo_tasks']:
            dsl = task['dsl'] or 'unknown'
            op = dsl.split('(')[0].split(':')[-1] if ':' in dsl else 'unknown'
            ops[op] = ops.get(op, 0) + 1
        
        for op, count in sorted(ops.items(), key=lambda x: -x[1]):
            print(f"  {op:15s}: {count} tasks")
    
    return results


def test_specific_task(task_id: str):
    """Test GEO-ENGINE on a specific task."""
    train_challenges, train_solutions = load_arc_dataset()
    
    if task_id not in train_challenges:
        print(f"Task {task_id} not found")
        return
    
    task_data = train_challenges[task_id]
    task_data['test'] = [{'input': train_solutions[task_id][0]}]
    
    core = ArcCore()
    trace = core.solve(task_data, task_id=task_id)
    
    print("=" * 60)
    print(f"Task: {task_id}")
    print("=" * 60)
    print(f"Success: {trace.success}")
    print(f"Method: {trace.method}")
    print(f"Time: {trace.execution_time:.3f}s")
    print(f"\nHypotheses tried: {len(trace.hypotheses_tried)}")
    
    for i, h in enumerate(trace.hypotheses_tried, 1):
        winner = " ← WINNER" if h == trace.winning_hypothesis else ""
        print(f"  {i}. {h.dsl_program:30s} conf={h.confidence:.2f}{winner}")
    
    if trace.winning_hypothesis:
        print(f"\nExplanation: {trace.winning_hypothesis.explanation}")
    
    print(f"\nReasoning: {trace.reasoning}")
    
    return trace


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test specific task
        task_id = sys.argv[1]
        test_specific_task(task_id)
    else:
        # Test on first 100 tasks
        results = test_geo_on_arc_tasks(max_tasks=100)
        
        # Save results
        output_file = Path("results") / "geo_engine_arc_results.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
