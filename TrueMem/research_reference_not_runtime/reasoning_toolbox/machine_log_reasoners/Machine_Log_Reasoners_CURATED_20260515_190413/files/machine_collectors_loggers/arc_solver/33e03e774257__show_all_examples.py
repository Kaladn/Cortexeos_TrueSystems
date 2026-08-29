import numpy as np
import json

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)
with open('arc-prize-2025/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = data['ac2e8ecf']

print('='*70)
print('TASK ac2e8ecf - ALL TRAINING EXAMPLES')
print('='*70)

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f'\n\n### EXAMPLE {i} ###')
    print(f'INPUT ({inp.shape[0]}x{inp.shape[1]}):')
    print(inp)
    print(f'\nOUTPUT ({out.shape[0]}x{out.shape[1]}):')
    print(out)

print('\n\n### TEST CASE ###')
test_in = np.array(task['test'][0]['input'])
test_out = np.array(solutions['ac2e8ecf'][0])

print(f'\nINPUT ({test_in.shape[0]}x{test_in.shape[1]}):')
print(test_in)
print(f'\nEXPECTED OUTPUT ({test_out.shape[0]}x{test_out.shape[1]}):')
print(test_out)
