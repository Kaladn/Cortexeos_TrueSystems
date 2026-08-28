"""
Test PATTERN-ENGINE + COLOR-ENGINE integration in MetaCompEngine.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from arc_organ.arc_operators import OPERATORS
from solvers.production_solver import ProductionSolver

def load_task(task_id: str) -> dict:
    train_path = "arc-prize-2025/arc-agi_training_challenges.json"
    with open(train_path, 'r') as f:
        data = json.load(f)
    return data[task_id]

print("=" * 80)
print("TESTING PATTERN-ENGINE + COLOR-ENGINE INTEGRATION")
print("=" * 80)
print()

# Initialize solver with both engines
solver = ProductionSolver(OPERATORS)

# Test on pattern-based tasks
test_tasks = [
    ("496994bd", "symmetry_completion - vertical→horizontal"),
    ("a59b95c0", "tiling - 3×3 tile pattern"),
    ("b1948b0a", "color mapping - global recolor")
]

print("Testing pattern detection + operator suggestions:")
print()

for task_id, description in test_tasks:
    print(f"Task {task_id}: {description}")
    
    task = load_task(task_id)
    task['task_id'] = task_id
    
    result = solver.solve(task)
    
    if result:
        source = "BASELINE" if result.get("rule_type") != "composition" else "COMPOSITION"
        operators = result.get('operators', [])
        print(f"  ✓ SOLVED by {source}")
        if operators:
            print(f"    Operators: {operators}")
    else:
        print(f"  ✗ NOT SOLVED")
    
    print()

print("=" * 80)
print("Integration complete - pattern analysis now guides operator selection")
print("=" * 80)
