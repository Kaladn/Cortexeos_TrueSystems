"""Visualize task b8cdaf2b"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ARC color palette
ARC_COLORS = [
    '#000000',  # 0: black
    '#0074D9',  # 1: blue
    '#FF4136',  # 2: red
    '#2ECC40',  # 3: green
    '#FFDC00',  # 4: yellow
    '#AAAAAA',  # 5: grey
    '#F012BE',  # 6: magenta
    '#FF851B',  # 7: orange
    '#7FDBFF',  # 8: sky
    '#870C25',  # 9: brown
]

cmap = ListedColormap(ARC_COLORS)

# Load task
data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
task_id = 'b8cdaf2b'
task = data[task_id]

num_examples = len(task['train'])

# Create figure
fig, axes = plt.subplots(num_examples, 2, figsize=(10, 4 * num_examples))

if num_examples == 1:
    axes = [axes]

fig.suptitle(f'Task {task_id}', fontsize=18, fontweight='bold')

for i, example in enumerate(task['train']):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    # Input
    ax_in = axes[i][0]
    ax_in.imshow(inp, cmap=cmap, vmin=0, vmax=9, interpolation='nearest')
    ax_in.set_title(f'Example {i+1} - Input ({inp.shape[0]}×{inp.shape[1]})', fontsize=14)
    ax_in.grid(True, which='both', color='lightgray', linewidth=0.5)
    ax_in.set_xticks(np.arange(-0.5, inp.shape[1], 1), minor=True)
    ax_in.set_yticks(np.arange(-0.5, inp.shape[0], 1), minor=True)
    ax_in.set_xticks(range(inp.shape[1]))
    ax_in.set_yticks(range(inp.shape[0]))
    
    # Output
    ax_out = axes[i][1]
    ax_out.imshow(out, cmap=cmap, vmin=0, vmax=9, interpolation='nearest')
    ax_out.set_title(f'Example {i+1} - Output ({out.shape[0]}×{out.shape[1]})', fontsize=14)
    ax_out.grid(True, which='both', color='lightgray', linewidth=0.5)
    ax_out.set_xticks(np.arange(-0.5, out.shape[1], 1), minor=True)
    ax_out.set_yticks(np.arange(-0.5, out.shape[0], 1), minor=True)
    ax_out.set_xticks(range(out.shape[1]))
    ax_out.set_yticks(range(out.shape[0]))

plt.tight_layout()
plt.savefig(f'{task_id}_visualization.png', dpi=150, bbox_inches='tight')
print(f'✓ Saved {task_id}_visualization.png')

# Also print the grids as numbers for analysis
print(f"\nTask {task_id} - {num_examples} training examples\n")
for i, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"Example {i}: {inp.shape[0]}×{inp.shape[1]}")
    print("Input:")
    for row in inp:
        print("  " + " ".join(str(x) for x in row))
    print("Output:")
    for row in out:
        print("  " + " ".join(str(x) for x in row))
    print()
