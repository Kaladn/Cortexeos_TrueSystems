"""
Deep dive into 0d3d703e to understand why mappings differ across examples.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np
from arc_organ.color_engine import ColorEngine


def load_task(task_id: str) -> dict:
    train_path = "arc-prize-2025/arc-agi_training_challenges.json"
    with open(train_path, 'r') as f:
        data = json.load(f)
    return data[task_id]


def analyze_task():
    task_id = "0d3d703e"
    task = load_task(task_id)
    engine = ColorEngine()
    
    print(f"Analyzing {task_id}")
    print(f"Examples: {len(task['train'])}")
    print()
    
    # Analyze each example
    for i, ex in enumerate(task['train']):
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        
        print(f"Example {i+1}:")
        print(f"  Input:\n{inp}")
        print(f"  Output:\n{out}")
        
        # Get mapping
        hyp = engine.infer_global_color_map(inp, out)
        if hyp:
            print(f"  Mapping: {hyp.mapping}")
            print(f"  Kind: {hyp.kind}")
        
        # Color analysis
        input_colors = engine.get_color_palette(inp)
        output_colors = engine.get_color_palette(out)
        print(f"  Input colors: {input_colors}")
        print(f"  Output colors: {output_colors}")
        print()
    
    print("=" * 60)
    print("OBSERVATION:")
    print("Different examples have different color palettes!")
    print("The mapping is NOT global across examples.")
    print("This requires LEARNING the mapping rule from structure.")
    print("=" * 60)


if __name__ == "__main__":
    analyze_task()
