import json
import matplotlib.pyplot as plt
import numpy as np

# Load dataset
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task_id = 'd5d6de2d'
task = data[task_id]

# ARC color palette
cmap = plt.cm.colors.ListedColormap([
    '#000000',  # 0 = black
    '#0074D9',  # 1 = blue
    '#FF4136',  # 2 = red
    '#2ECC40',  # 3 = green
    '#FFDC00',  # 4 = yellow
    '#AAAAAA',  # 5 = gray
    '#F012BE',  # 6 = magenta
    '#FF851B',  # 7 = orange
    '#7FDBFF',  # 8 = cyan
    '#870C25',  # 9 = brown
])

num_examples = len(task['train'])
fig, axes = plt.subplots(num_examples, 2, figsize=(8, num_examples * 3))

if num_examples == 1:
    axes = [axes]

for i, example in enumerate(task['train']):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    # Input
    ax = axes[i][0]
    ax.imshow(inp, cmap=cmap, vmin=0, vmax=9)
    ax.set_title(f'Example {i+1}: Input ({inp.shape[0]}×{inp.shape[1]})', fontweight='bold')
    ax.set_xticks(range(inp.shape[1]))
    ax.set_yticks(range(inp.shape[0]))
    ax.grid(True, color='white', linewidth=0.5)
    ax.tick_params(labelsize=8)
    
    # Output
    ax = axes[i][1]
    ax.imshow(out, cmap=cmap, vmin=0, vmax=9)
    ax.set_title(f'Example {i+1}: Output ({out.shape[0]}×{out.shape[1]})', fontweight='bold')
    ax.set_xticks(range(out.shape[1]))
    ax.set_yticks(range(out.shape[0]))
    ax.grid(True, color='white', linewidth=0.5)
    ax.tick_params(labelsize=8)

fig.suptitle(f'Task: {task_id}', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig(f'task_{task_id}_visual.png', dpi=150, bbox_inches='tight')
print(f"Saved visualization to: task_{task_id}_visual.png")
plt.show()
