"""Quick smoke test: Verify 10 known solves still work."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from arc_organ.arc_operators import OPERATORS
from solvers.production_solver import ProductionSolver

# Load dataset
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    train_data = json.load(f)

# Initialize solver
solver = ProductionSolver(OPERATORS)

# Test 10 known solves
known_solves = [
    "007bbfb7", "009d5c81", "05269061", "0d3d703e", "1cf80156",
    "25d8a9c8", "25ff71a9", "332efdb3", "3befdf3e", "3c9b0459"
]

print("SMOKE TEST: Verifying 10 known solves")
print("=" * 60)

passed = 0
failed = []

for task_id in known_solves:
    task = train_data[task_id]
    task['task_id'] = task_id
    
    result = solver.solve(task)
    
    if result:
        passed += 1
        print(f"✓ {task_id}")
    else:
        failed.append(task_id)
        print(f"✗ {task_id} - REGRESSION!")

print()
print("=" * 60)
print(f"RESULT: {passed}/10 passed")

if failed:
    print(f"FAILED: {failed}")
    print("⚠ REGRESSIONS DETECTED")
else:
    print("✓ ALL TESTS PASSED - NO REGRESSIONS")
    print("System stable for production")

print("=" * 60)
