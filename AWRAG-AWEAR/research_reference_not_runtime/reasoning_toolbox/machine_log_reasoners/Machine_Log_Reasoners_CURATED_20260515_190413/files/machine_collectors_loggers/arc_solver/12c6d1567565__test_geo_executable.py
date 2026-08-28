"""
Test GEO-ENGINE on the 11 executable tasks
"""

import json
import numpy as np
from pathlib import Path
from arc_core import ArcCore


# 11 tasks that should be solvable by GEO-ENGINE now
GEO_EXECUTABLE_TASKS = [
    '25ff71a9',  # TRANSLATE
    '3c9b0459',  # ROTATE 180
    '60c09cac',  # SCALE 2
    '6150a2bd',  # ROTATE 180
    '67a3c6ac',  # FLIP HORIZONTAL
    '68b16354',  # FLIP VERTICAL
    '74dd1130',  # TRANSPOSE
    '9172f3a0',  # SCALE 3
    '9dfd6313',  # TRANSPOSE
    'c59eb873',  # SCALE 2
    'ed36ccf7',  # ROTATE 90
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


def test_geo_executable():
    """Test GEO-ENGINE on 11 executable tasks."""
    core = ArcCore()
    
    results = {
        'total': len(GEO_EXECUTABLE_TASKS),
        'solved': 0,
        'tasks': []
    }
    
    print("=" * 60)
    print("GEO-ENGINE: Testing 11 Executable Tasks")
    print("=" * 60)
    print()
    
    for task_id in GEO_EXECUTABLE_TASKS:
        task_data, expected_output = load_task(task_id)
        trace = core.solve(task_data, task_id=task_id)
        
        success_mark = "✓" if trace.success else "✗"
        
        results['tasks'].append({
            'task_id': task_id,
            'success': trace.success,
            'method': trace.method,
            'dsl': trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else None
        })
        
        if trace.success:
            results['solved'] += 1
        
        print(f"{success_mark} {task_id}: {trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else 'FAILED'}")
    
    print()
    print("=" * 60)
    print(f"RESULTS: {results['solved']}/{results['total']} solved ({results['solved']/results['total']*100:.0f}%)")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    results = test_geo_executable()
    
    # Save results
    output_file = Path("results") / "geo_engine_executable_results.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
