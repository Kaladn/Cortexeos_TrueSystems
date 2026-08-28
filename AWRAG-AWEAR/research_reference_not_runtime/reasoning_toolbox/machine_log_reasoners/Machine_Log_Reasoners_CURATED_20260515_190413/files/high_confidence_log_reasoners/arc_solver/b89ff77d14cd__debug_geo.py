"""Find tasks that ARE purely geometric"""

import json
import numpy as np
from pathlib import Path
from engines.geo_engine import GeoEngine
from engines.base_engine import TaskView


# Load all tasks
with open("arc-prize-2025/arc-agi_training_challenges.json") as f:
    challenges = json.load(f)

geo = GeoEngine()
geo_tasks = []

print("Scanning 400 training tasks for pure geometry...\n")

for task_id, task_data in list(challenges.items()):
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
    
    # Test GEO-ENGINE
    hypotheses = geo.analyze(task_view)
    
    if hypotheses:
        geo_tasks.append({
            'task_id': task_id,
            'operations': [h.dsl_program for h in hypotheses],
            'best': hypotheses[0].dsl_program,
            'explanation': hypotheses[0].explanation
        })
        print(f"✓ {task_id}: {hypotheses[0].dsl_program}")

print(f"\n{'='*60}")
print(f"PURE GEOMETRIC TASKS: {len(geo_tasks)}/400")
print(f"{'='*60}")

if geo_tasks:
    print("\nBy operation:")
    ops = {}
    executable = 0
    for task in geo_tasks:
        op = task['best'].split('(')[0].split(':')[1]
        ops[op] = ops.get(op, 0) + 1
        # CROP not yet executable
        if op != 'CROP':
            executable += 1
    
    for op, count in sorted(ops.items(), key=lambda x: -x[1]):
        exec_mark = "" if op == "CROP" else " (executable)"
        print(f"  {op:12s}: {count}{exec_mark}")
    
    print(f"\n{executable} tasks executable NOW (non-CROP)")
    print(f"{ops.get('CROP', 0)} tasks need CROP implementation")
    
    print("\nExecutable tasks (rotate/flip/scale/transpose/translate):")
    for task in geo_tasks:
        op = task['best'].split('(')[0].split(':')[1]
        if op != 'CROP':
            print(f"  {task['task_id']}: {task['best']}")
else:
    print("\nNo purely geometric tasks found in first 400.")
