"""
Test COLOR-ENGINE Phase 1 on real ARC tasks from the rule database.
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


def test_color_rules():
    """Test COLOR-ENGINE on real ARC tasks with color transformation rules."""
    print("=" * 80)
    print("TESTING COLOR-ENGINE ON REAL ARC TASKS")
    print("=" * 80)
    print()
    
    engine = ColorEngine(mapping_threshold=0.95)
    
    # Load rule database to find COLOR-ENGINE tasks
    with open("arc_rules_with_math_expansion.jsonl", 'r') as f:
        rules = [json.loads(line) for line in f]
    
    # Filter for COLOR-ENGINE rules (check nested engine_hints in math_expansion_slot)
    color_rules = []
    for r in rules:
        engine_hints = r.get('math_expansion_slot', {}).get('engine_hints', [])
        if "COLOR-ENGINE" in engine_hints:
            color_rules.append(r)
    
    print(f"Found {len(color_rules)} COLOR-ENGINE rules in database")
    print()
    
    # Test sample of color rules (first 10)
    test_tasks = color_rules[:10]
    
    results = []
    
    for i, rule in enumerate(test_tasks, 1):
        task_id = rule['task_id']
        operator = rule['operator']
        
        print(f"[{i}/{len(test_tasks)}] Testing {task_id} (operator: {operator})")
        
        try:
            task = load_task(task_id)
            
            # Get first training example
            train_example = task['train'][0]
            inp = np.array(train_example['input'])
            out = np.array(train_example['output'])
            
            print(f"  Input shape: {inp.shape}, Output shape: {out.shape}")
            
            # Test global color mapping
            hyp = engine.infer_global_color_map(inp, out)
            
            if hyp:
                print(f"  ✓ Color mapping detected: {hyp.kind} (score {hyp.score:.3f})")
                print(f"    Mapping: {dict(list(hyp.mapping.items())[:5])}")
                
                # Test if mapping works on all training examples
                consistent = True
                for j, ex in enumerate(task['train']):
                    ex_in = np.array(ex['input'])
                    ex_out = np.array(ex['output'])
                    
                    if ex_in.shape != ex_out.shape:
                        consistent = False
                        break
                    
                    predicted = engine.apply_color_map(ex_in, hyp.mapping)
                    if not np.array_equal(predicted, ex_out):
                        consistent = False
                        break
                
                if consistent:
                    print(f"    ✓✓ CONSISTENT across all {len(task['train'])} training examples!")
                    results.append({'task_id': task_id, 'status': 'perfect', 'operator': operator})
                else:
                    print(f"    ⚠ Inconsistent across examples (complex rule)")
                    results.append({'task_id': task_id, 'status': 'partial', 'operator': operator})
            else:
                print(f"  ✗ No valid color mapping (may need Phase 2+)")
                results.append({'task_id': task_id, 'status': 'no_mapping', 'operator': operator})
            
            # Additional color analysis
            bg_preserved, bg_color = engine.detect_background_preservation(inp, out)
            new_colors = engine.detect_new_colors(inp, out)
            removed_colors = engine.detect_removed_colors(inp, out)
            
            print(f"  Background preserved: {bg_preserved} (color={bg_color})")
            if new_colors:
                print(f"  New colors: {new_colors}")
            if removed_colors:
                print(f"  Removed colors: {removed_colors}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'task_id': task_id, 'status': 'error', 'operator': operator})
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    perfect = sum(1 for r in results if r['status'] == 'perfect')
    partial = sum(1 for r in results if r['status'] == 'partial')
    no_map = sum(1 for r in results if r['status'] == 'no_mapping')
    errors = sum(1 for r in results if r['status'] == 'error')
    
    print(f"Perfect (consistent across all examples): {perfect}/{len(results)}")
    print(f"Partial (detected but inconsistent): {partial}/{len(results)}")
    print(f"No mapping (needs advanced features): {no_map}/{len(results)}")
    print(f"Errors: {errors}/{len(results)}")
    print()
    
    if perfect > 0:
        print("Perfect matches:")
        for r in results:
            if r['status'] == 'perfect':
                print(f"  - {r['task_id']} ({r['operator']})")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    test_color_rules()
