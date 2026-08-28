"""
MANUAL MATH FORMALIZATION - Next 5 Unsolved Tasks

Path B: Analyze unsolved tasks, derive transformation rules, 
write mathematical DSL specs as blueprints for future operators.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

print("="*80)
print("MANUAL MATH FORMALIZATION - NEXT 5 UNSOLVED TASKS")
print("="*80)
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

with open('math_dsl_solutions_2025.json') as f:
    solved = json.load(f)

unsolved_ids = sorted([tid for tid in all_data.keys() if tid not in solved])

print(f"Total unsolved: {len(unsolved_ids)}")
print()

# Select first 5 unsolved for manual analysis
target_tasks = unsolved_ids[:5]

print("Target tasks for manual formalization:")
for i, tid in enumerate(target_tasks, 1):
    print(f"  {i}. {tid}")
print()

def visualize_task(task_id, task_data):
    """Display task examples for human analysis."""
    print("="*80)
    print(f"TASK: {task_id}")
    print("="*80)
    print()
    
    for idx, example in enumerate(task_data['train']):
        inp = np.array(example['input'])
        out = np.array(example['output'])
        
        print(f"Example {idx + 1}:")
        print(f"  Input shape: {inp.shape}")
        print(f"  Output shape: {out.shape}")
        print(f"  Input colors: {sorted(set(inp.flatten()))}")
        print(f"  Output colors: {sorted(set(out.flatten()))}")
        print()
        
        print("  Input:")
        print_grid(inp)
        print()
        
        print("  Output:")
        print_grid(out)
        print()
    
    return task_data

def print_grid(grid, max_width=20, max_height=20):
    """Print grid with color coding."""
    h, w = grid.shape
    if h > max_height or w > max_width:
        print(f"    [Grid too large: {h}x{w} - showing dimensions only]")
        return
    
    for row in grid:
        line = "    "
        for val in row:
            if val == 0:
                line += ". "
            else:
                line += f"{val} "
        print(line)

def analyze_and_formalize(task_id, task_data):
    """Human-guided analysis to create math DSL."""
    
    print(f"\n{'='*80}")
    print(f"MATHEMATICAL FORMALIZATION: {task_id}")
    print(f"{'='*80}\n")
    
    # Show the task
    visualize_task(task_id, task_data)
    
    # This is where human insight goes
    # For now, return a template that will be filled manually
    
    math_dsl = {
        'task_id': task_id,
        'pattern_type': 'TO_BE_DETERMINED',
        'human_description': 'Manual analysis required',
        'math_dsl': {
            'objects': [
                'TO_BE_DEFINED: Grid properties, shapes, patterns'
            ],
            'conditions': [
                'TO_BE_DEFINED: Invariants and constraints'
            ],
            'equations': [
                'TO_BE_DEFINED: Mathematical relationships'
            ],
            'transform': [
                'TO_BE_DEFINED: Step-by-step algorithm in math form'
            ]
        },
        'operator_blueprint': {
            'name': 'TO_BE_NAMED',
            'category': 'TO_BE_CLASSIFIED',
            'preconditions': ['TO_BE_DEFINED'],
            'implementation_notes': 'TO_BE_WRITTEN'
        },
        'examples': []
    }
    
    # Add examples
    for example in task_data['train']:
        math_dsl['examples'].append({
            'input': np.array(example['input']).tolist(),
            'output': np.array(example['output']).tolist()
        })
    
    return math_dsl

# Process first 5 tasks
print("="*80)
print("PROCESSING TASKS")
print("="*80)
print()

formalizations = []

for task_id in target_tasks:
    task_data = all_data[task_id]
    formalization = analyze_and_formalize(task_id, task_data)
    formalizations.append(formalization)
    print()

# Save templates for manual editing
output_file = 'manual_math_dsl_templates.jsonl'
with open(output_file, 'w') as f:
    for form in formalizations:
        f.write(json.dumps(form, indent=2) + '\n')

print("="*80)
print("TEMPLATES GENERATED")
print("="*80)
print()
print(f"Created {len(formalizations)} math DSL templates")
print(f"Saved to: {output_file}")
print()
print("Next steps:")
print("  1. Manually analyze each task's transformation pattern")
print("  2. Fill in the math DSL fields:")
print("     - objects: Define mathematical entities")
print("     - conditions: State invariants")
print("     - equations: Write formal relationships")
print("     - transform: Describe algorithm mathematically")
print("  3. Design operator based on math spec")
print("  4. Implement and test")
print()
print("Task IDs to analyze:")
for i, tid in enumerate(target_tasks, 1):
    print(f"  {i}. {tid}")
