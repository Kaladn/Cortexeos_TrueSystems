"""Create visual grid images for task 05269061."""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

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
    '#7FDBFF',  # 8: cyan
    '#870C25',  # 9: maroon
]

def plot_grid(grid, title, ax):
    """Plot a grid with ARC colors."""
    cmap = ListedColormap(ARC_COLORS)
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=9)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.grid(True, which='both', color='white', linewidth=0.5)
    ax.set_xticks(np.arange(-0.5, grid.shape[1], 1))
    ax.set_yticks(np.arange(-0.5, grid.shape[0], 1))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(length=0)

# Create figure with all examples
fig = plt.figure(figsize=(16, 12))

# Training examples
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    # Input
    ax = plt.subplot(4, 4, (i-1)*4 + 1)
    non_zero = sorted(set(inp.flatten()) - {0})
    plot_grid(inp, f'Train {i} - Input\nColors: {non_zero}', ax)
    
    # Output
    ax = plt.subplot(4, 4, (i-1)*4 + 2)
    plot_grid(out, f'Train {i} - Output', ax)
    
    # 3x3 pattern
    ax = plt.subplot(4, 4, (i-1)*4 + 3)
    pattern_3x3 = out[:3, :3]
    plot_grid(pattern_3x3, f'Train {i} - 3x3 Pattern', ax)

# Test
test_inp = np.array(task['test'][0]['input'])
test_out = np.array(solutions['05269061'][0])

# Test input
ax = plt.subplot(4, 4, 13)
non_zero = sorted(set(test_inp.flatten()) - {0})
plot_grid(test_inp, f'Test - Input\nColors: {non_zero}', ax)

# Test output
ax = plt.subplot(4, 4, 14)
plot_grid(test_out, 'Test - Output', ax)

# Test 3x3 pattern
ax = plt.subplot(4, 4, 15)
pattern_3x3 = test_out[:3, :3]
plot_grid(pattern_3x3, 'Test - 3x3 Pattern', ax)

plt.suptitle('Task 05269061 - Visual Analysis\nRule: Extract non-zero colors, create 3x3 repeating pattern', 
             fontsize=14, fontweight='bold', y=0.98)

plt.tight_layout()
plt.savefig('task_05269061_visual.png', dpi=150, bbox_inches='tight')
print("✅ Saved: task_05269061_visual.png")

# Create a second figure focusing on the pattern comparison
fig2 = plt.figure(figsize=(14, 8))

examples = [
    ("Train 1", task['train'][0], [2, 3, 8]),
    ("Train 2", task['train'][1], [1, 2, 4]),
    ("Train 3", task['train'][2], [3, 4, 8]),
    ("Test", {'input': test_inp, 'output': test_out}, [1, 2, 4]),
]

for i, (label, ex, colors) in enumerate(examples, 1):
    inp = np.array(ex['input'])
    if 'output' in ex:
        out = np.array(ex['output'])
    else:
        out = test_out if label == "Test" else np.array(ex['output'])
    
    # Input
    ax = plt.subplot(2, 8, i)
    plot_grid(inp, f'{label} Input', ax)
    
    # Output 3x3
    ax = plt.subplot(2, 8, i + 4)
    pattern = out[:3, :3]
    
    # Add text labels on the pattern
    plot_grid(pattern, f'{label} Output Pattern', ax)
    for r in range(3):
        for c in range(3):
            val = int(pattern[r, c])
            ax.text(c, r, str(val), ha='center', va='center', 
                   color='white', fontsize=12, fontweight='bold')
    
    # Add color legend
    ax = plt.subplot(2, 8, i + 8)
    ax.text(0.5, 0.7, f'Colors: {colors}', ha='center', va='center', 
           fontsize=9, transform=ax.transAxes)
    
    # Show pattern sequence
    seq = [int(pattern[0, 0]), int(pattern[0, 1]), int(pattern[0, 2])]
    ax.text(0.5, 0.3, f'Start: [{seq[0]}, {seq[1]}, {seq[2]}]', 
           ha='center', va='center', fontsize=9, transform=ax.transAxes,
           fontweight='bold', color='red')
    ax.axis('off')

plt.suptitle('Pattern Comparison - Notice Training 2 and Test have SAME colors {1,2,4} but DIFFERENT patterns!', 
             fontsize=12, fontweight='bold', color='red')

plt.tight_layout()
plt.savefig('task_05269061_pattern_comparison.png', dpi=150, bbox_inches='tight')
print("✅ Saved: task_05269061_pattern_comparison.png")

print("\n" + "="*80)
print("KEY INSIGHT:")
print("="*80)
print("Training 2: colors {1,2,4} → pattern [2, 4, 1]")
print("Test:       colors {1,2,4} → pattern [2, 1, 4]")
print("\nSame input colors, DIFFERENT output ordering!")
print("The spatial arrangement of input colors determines output sequence.")
