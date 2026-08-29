"""Test GEO-ENGINE on ALL 59 geometric tasks (including CROP)"""

import json
import numpy as np
from pathlib import Path
from arc_core import ArcCore


# All 59 geometric tasks
GEO_ALL_TASKS = [
    '0b148d64', '1190e5a7', '1a2e2828', '1a6449f1', '1c786137', '1cf80156',
    '1f85a75f', '2013d3e2', '239be575', '23b5c85d', '25ff71a9', '2c0b0aff',
    '2dc579da', '3194b014', '358ba94e', '39a8645d', '3c9b0459', '3f7978a0',
    '48d8fb45', '5bd6f4ac', '60c09cac', '6150a2bd', '642d658d', '67a3c6ac',
    '68b16354', '7039b2d7', '72ca375d', '73182012', '73ccf9c2', '74dd1130',
    '7bb29440', '88a62173', '8efcae92', '9172f3a0', '9a4bb226', '9ba4a9aa',
    '9dfd6313', 'a644e277', 'a6953f00', 'ae4f1146', 'aee291af', 'b9b7f026',
    'be94b721', 'bf699163', 'c3202e5a', 'c59eb873', 'c909285e', 'cd3c21df',
    'ce602527', 'd10ecb37', 'd56f2372', 'd9fac9be', 'da6e95e5', 'de1cd16c',
    'e50d258f', 'e872b94a', 'ed36ccf7', 'f5aa3634', 'f9012d9b'
]


def load_task(task_id):
    """Load task from dataset."""
    with open("arc-prize-2025/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    
    with open("arc-prize-2025/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)
    
    task_data = challenges[task_id]
    task_data['test'] = [{'input': solutions[task_id][0]}]
    
    return task_data, solutions[task_id][0]


def test_all_geo_tasks():
    """Test GEO-ENGINE on all 59 geometric tasks."""
    core = ArcCore()
    
    results = {
        'total': len(GEO_ALL_TASKS),
        'solved': 0,
        'failed': 0,
        'by_operation': {},
        'tasks': []
    }
    
    print("=" * 60)
    print("GEO-ENGINE: Testing ALL 59 Geometric Tasks")
    print("=" * 60)
    print()
    
    for i, task_id in enumerate(GEO_ALL_TASKS, 1):
        task_data, expected_output = load_task(task_id)
        trace = core.solve(task_data, task_id=task_id)
        
        success = trace.success
        dsl = trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else None
        
        results['tasks'].append({
            'task_id': task_id,
            'success': success,
            'dsl': dsl
        })
        
        if success:
            results['solved'] += 1
            op = dsl.split('(')[0].split(':')[1] if dsl else 'unknown'
            results['by_operation'][op] = results['by_operation'].get(op, 0) + 1
            mark = "✓"
        else:
            results['failed'] += 1
            mark = "✗"
        
        print(f"[{i:2d}/{results['total']}] {mark} {task_id}: {dsl or 'FAILED'}")
    
    print()
    print("=" * 60)
    print(f"RESULTS: {results['solved']}/{results['total']} solved ({results['solved']/results['total']*100:.1f}%)")
    print("=" * 60)
    
    if results['by_operation']:
        print("\nBy operation:")
        for op, count in sorted(results['by_operation'].items(), key=lambda x: -x[1]):
            print(f"  {op:12s}: {count}")
    
    if results['failed'] > 0:
        print(f"\n{results['failed']} failures (CROP execution might need debugging)")
    
    return results


if __name__ == "__main__":
    results = test_all_geo_tasks()
    
    # Save results
    output_file = Path("results") / "geo_engine_all_results.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
