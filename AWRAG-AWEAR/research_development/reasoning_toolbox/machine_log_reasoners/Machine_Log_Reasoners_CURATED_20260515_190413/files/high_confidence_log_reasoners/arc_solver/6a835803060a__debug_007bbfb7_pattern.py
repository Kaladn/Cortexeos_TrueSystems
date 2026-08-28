import numpy as np
import json

task = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))['007bbfb7']
inp = np.array(task['train'][0]['input'])
out = np.array(task['train'][0]['output'])

tiled = np.tile(inp, (3,3))
print('Simple tiled:\n', tiled)
print('\nActual output:\n', out)
print('\nAre they equal?', np.array_equal(tiled, out))

print('\nDifferences:')
diff = (tiled != out)
print('Num differences:', np.sum(diff))

coords = np.argwhere(diff)[:10]
print('First 10 diff coords:')
for r,c in coords:
    print(f'  ({r},{c}): tiled={tiled[r,c]}, out={out[r,c]}')

# Check self-referential pattern
mask = np.tile(inp != 0, (3,3))
masked_tiled = tiled * mask
print('\nSelf-referential (mask non-background):')
print(masked_tiled)
print('\nMatches output?', np.array_equal(masked_tiled, out))

# Check if zeros in input propagate to output
print('\nInput has 0s at positions:')
zero_pos = np.argwhere(inp == 0)
print(zero_pos)
