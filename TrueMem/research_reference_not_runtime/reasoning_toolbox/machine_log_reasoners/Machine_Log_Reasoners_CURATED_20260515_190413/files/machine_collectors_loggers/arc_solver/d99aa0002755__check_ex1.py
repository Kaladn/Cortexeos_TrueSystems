import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

d = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
ex = d['ac2e8ecf']['train'][0]
inp = np.array(ex['input'])
expected = np.array(ex['output'])

op = CenterRepulsionOperator()
result = op.apply(inp, {})

match = np.array_equal(result, expected)
print(f'Example 1: {"PASS" if match else "FAIL"}')

if not match:
    diffs = np.sum(result != expected)
    print(f'Differences: {diffs} cells')
    print('\nExpected:')
    print(expected)
    print('\nGot:')
    print(result)
    print('\nDiff mask:')
    print((result != expected).astype(int))
