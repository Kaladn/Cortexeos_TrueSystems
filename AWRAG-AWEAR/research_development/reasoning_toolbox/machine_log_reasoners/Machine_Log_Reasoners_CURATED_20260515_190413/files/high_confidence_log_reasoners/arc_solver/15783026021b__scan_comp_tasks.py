"""
Scan for COMP-ENGINE tasks (bounding box crop, object extraction)
"""

import json
import numpy as np
from pathlib import Path
from engines.color_engine import CompEngine
from engines.base_engine import TaskView


def load_dataset():
    """Load ARC 2025 dataset."""
    with open("arc-prize-2025/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    
    with open("arc-prize-2025/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)
    
    return challenges, solutions


def scan_for_comp_tasks():
    """Scan training set for COMP-ENGINE patterns."""
    challenges, solutions = load_dataset()
    comp_engine = CompEngine()
    
    comp_tasks = []
    
    print("Scanning for COMP (object/blob) tasks...")
    print()
    
    for task_id, task_data in challenges.items():
        # Parse to TaskView
        train_pairs = []
        for example in task_data['train']:
            input_grid = np.array(example['input'])
            output_grid = np.array(example['output'])
            train_pairs.append((input_grid, output_grid))
        
        test_input = np.array(task_data['test'][0]['input'])
        
        task_view = TaskView(
            train_pairs=train_pairs,
            test_input=test_input,
            task_id=task_id,
            metadata={}
        )
        
        # Test COMP-ENGINE
        hypotheses = comp_engine.analyze(task_view)
        
        if hypotheses:
            comp_tasks.append({
                'task_id': task_id,
                'operations': [h.dsl_program for h in hypotheses],
                'best': hypotheses[0].dsl_program,
                'confidence': hypotheses[0].confidence,
                'explanation': hypotheses[0].explanation
            })
            print(f"✓ {task_id}: {hypotheses[0].dsl_program} (conf={hypotheses[0].confidence:.2f})")
    
    print()
    print("=" * 60)
    print(f"COMP TASKS DETECTED: {len(comp_tasks)}/1000")
    print("=" * 60)
    
    if comp_tasks:
        print("\nBy operation:")
        ops = {}
        for task in comp_tasks:
            op = task['best'].split('(')[0].split(':')[1]
            ops[op] = ops.get(op, 0) + 1
        
        for op, count in sorted(ops.items(), key=lambda x: -x[1]):
            print(f"  {op:20s}: {count}")
        
        print(f"\nFirst 20 COMP tasks:")
        for task in comp_tasks[:20]:
            print(f"  {task['task_id']}: {task['best']}")
    
    return comp_tasks


if __name__ == "__main__":
    comp_tasks = scan_for_comp_tasks()
    
    # Save results
    output_file = Path("results") / "comp_engine_scan.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(comp_tasks, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
