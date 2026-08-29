"""Show a specific task"""
import json
import numpy as np

data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
task_id = 'b8cdaf2b'  # Small 5×5 task
task = data[task_id]

print(f"TASK: {task_id}")
print(f"Training examples: {len(task['train'])}\n")

for i, ex in enumerate(task['train'], 1):
    print(f"\nExample {i}:")
    print("Input:")
    for row in ex['input']:
        print(" ", row)
    print("Output:")
    for row in ex['output']:
        print(" ", row)
