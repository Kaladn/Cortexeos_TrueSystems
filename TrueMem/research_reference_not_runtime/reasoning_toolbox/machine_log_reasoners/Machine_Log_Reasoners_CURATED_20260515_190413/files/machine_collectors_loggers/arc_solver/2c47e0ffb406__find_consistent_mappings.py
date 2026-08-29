"""Find tasks with CONSISTENT color mapping across all training pairs"""

import json
import numpy as np
from pathlib import Path


def load_dataset():
    with open("arc-prize-2025/arc-agi_training_challenges.json") as f:
        return json.load(f)


def check_consistent_mapping(task_data):
    """Check if task has consistent color mapping across all pairs."""
    all_mappings = []
    
    for example in task_data['train']:
        inp = np.array(example['input'])
        out = np.array(example['output'])
        
        # Must be same shape
        if inp.shape != out.shape:
            return None
        
        # Build mapping for this pair
        mapping = {}
        for i in range(inp.shape[0]):
            for j in range(inp.shape[1]):
                in_c = int(inp[i, j])
                out_c = int(out[i, j])
                
                if in_c not in mapping:
                    mapping[in_c] = out_c
                elif mapping[in_c] != out_c:
                    return None  # Inconsistent within pair
        
        all_mappings.append(mapping)
    
    # Check all pairs have SAME mapping
    if not all_mappings:
        return None
    
    first_mapping = all_mappings[0]
    if not all(m == first_mapping for m in all_mappings):
        return None  # Differs across pairs
    
    # Check not identity
    if all(k == v for k, v in first_mapping.items()):
        return None
    
    return first_mapping


def main():
    challenges = load_dataset()
    
    consistent_tasks = []
    
    print("Scanning for consistent color mapping tasks...")
    print()
    
    for task_id, task_data in challenges.items():
        mapping = check_consistent_mapping(task_data)
        
        if mapping:
            consistent_tasks.append({
                'task_id': task_id,
                'mapping': mapping
            })
            mapping_str = ", ".join(f"{k}→{v}" for k, v in sorted(mapping.items()) if k != v)
            print(f"✓ {task_id}: {mapping_str}")
    
    print()
    print()
    print("=" * 60)
    print(f"CONSISTENT MAPPING TASKS: {len(consistent_tasks)}/1000")
    print("=" * 60)
    
    # Save
    output_file = Path("results") / "consistent_color_mappings.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(consistent_tasks, f, indent=2)
    
    print(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    main()
