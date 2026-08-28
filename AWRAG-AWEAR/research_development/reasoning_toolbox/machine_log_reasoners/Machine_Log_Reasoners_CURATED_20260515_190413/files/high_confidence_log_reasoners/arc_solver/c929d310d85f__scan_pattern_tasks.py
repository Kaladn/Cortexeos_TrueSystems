"""Scan for PATTERN-ENGINE tasks"""

import json
import numpy as np
from pathlib import Path
from engines.color_engine import PatternEngine
from engines.base_engine import TaskView


def load_dataset():
    with open("arc-prize-2025/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    
    with open("arc-prize-2025/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)
    
    return challenges, solutions


def scan_for_pattern_tasks():
    challenges, solutions = load_dataset()
    pattern_engine = PatternEngine()
    
    pattern_tasks = []
    
    print("Scanning for PATTERN (tiling/stripes) tasks...")
    print()
    
    for task_id, task_data in challenges.items():
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
        
        hypotheses = pattern_engine.analyze(task_view)
        
        if hypotheses:
            pattern_tasks.append({
                'task_id': task_id,
                'best': hypotheses[0].dsl_program,
                'confidence': hypotheses[0].confidence
            })
            print(f"✓ {task_id}: {hypotheses[0].dsl_program}")
    
    print()
    print("=" * 60)
    print(f"PATTERN TASKS: {len(pattern_tasks)}/1000")
    print("=" * 60)
    
    if pattern_tasks:
        ops = {}
        for task in pattern_tasks:
            op = task['best'].split('(')[0].split(':')[1]
            ops[op] = ops.get(op, 0) + 1
        
        print("\nBy operation:")
        for op, count in sorted(ops.items(), key=lambda x: -x[1]):
            print(f"  {op:20s}: {count}")
    
    return pattern_tasks


if __name__ == "__main__":
    pattern_tasks = scan_for_pattern_tasks()
    
    output_file = Path("results") / "pattern_engine_scan.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(pattern_tasks, f, indent=2)
    
    print(f"\nSaved to: {output_file}")
