"""
Test COLOR-ENGINE on recolor_mapping tasks (should have consistent global mappings).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np
from arc_organ.color_engine import ColorEngine


def load_task(task_id: str) -> dict:
    """Load task from ARC 2025 dataset."""
    train_path = "arc-prize-2025/arc-agi_training_challenges.json"
    
    with open(train_path, 'r') as f:
        data = json.load(f)
    
    if task_id in data:
        return data[task_id]
    
    raise ValueError(f"Task {task_id} not found")


def test_recolor_mapping_tasks():
    """Test COLOR-ENGINE on recolor_mapping tasks (should be pure global mappings)."""
    print("=" * 80)
    print("TESTING COLOR-ENGINE ON recolor_mapping TASKS")
    print("=" * 80)
    print()
    
    engine = ColorEngine(mapping_threshold=0.95)
    
    # Load rule database
    with open("arc_rules_with_math_expansion.jsonl", 'r') as f:
        rules = [json.loads(line) for line in f]
    
    # Filter for recolor_mapping operator (ensure no composition rules)
    recolor_tasks = [r for r in rules if r.get('operator') == 'recolor_mapping' and r.get('rule_type') == 'single_operator']
    
    print(f"Found {len(recolor_tasks)} recolor_mapping tasks")
    print()
    
    perfect_count = 0
    
    for i, rule in enumerate(recolor_tasks, 1):
        task_id = rule['task_id']
        
        print(f"[{i}/{len(recolor_tasks)}] Testing {task_id}")
        
        try:
            task = load_task(task_id)
            
            # Convert all examples
            train_pairs = [(np.array(ex['input']), np.array(ex['output'])) 
                          for ex in task['train']]
            
            # Test detection across all examples
            hyps = engine.detect_color_transformations(train_pairs)
            
            if hyps:
                hyp = hyps[0]
                print(f"  ✓✓ PERFECT GLOBAL MAPPING DETECTED")
                print(f"     Kind: {hyp.kind}, Score: {hyp.score:.3f}")
                print(f"     Mapping: {hyp.mapping}")
                print(f"     Validated on: {hyp.params['validated_on']} examples")
                perfect_count += 1
            else:
                print(f"  ✗ No consistent mapping (unexpected for recolor_mapping!)")
                
                # Debug: try first pair
                inp, out = train_pairs[0]
                hyp = engine.infer_global_color_map(inp, out)
                if hyp:
                    print(f"    First example has mapping: {hyp.mapping}")
                    print(f"    But fails on other examples (WHY?)")
        
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print()
    
    print("=" * 80)
    print(f"PERFECT MAPPINGS: {perfect_count}/{len(recolor_tasks)}")
    print("=" * 80)


if __name__ == "__main__":
    test_recolor_mapping_tasks()
