"""
Test PATTERN-ENGINE on real ARC tasks from rule database.
Validate symmetry detection against known symmetry-based solutions.
"""
import json
import numpy as np
from pathlib import Path
from arc_organ.pattern_engine import PatternEngine


def load_arc_tasks():
    """Load ARC task data."""
    train_data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
    eval_data = json.load(open('arc-prize-2025/arc-agi_evaluation_challenges.json'))
    return {**train_data, **eval_data}


def test_pattern_engine_on_rules():
    """Test PATTERN-ENGINE on tasks from rule database."""
    
    # Load rule database
    rules = [json.loads(line) for line in open('arc_rules_with_math_expansion.jsonl')]
    
    # Filter to PATTERN-ENGINE rules
    pattern_rules = [r for r in rules 
                    if 'PATTERN-ENGINE' in r.get('math_expansion_slot', {}).get('engine_hints', [])]
    
    print("=" * 80)
    print("PATTERN-ENGINE: REAL ARC TASK VALIDATION")
    print("=" * 80)
    print()
    print(f"Testing on {len(pattern_rules)} PATTERN-ENGINE tasks")
    print()
    
    # Load task data
    all_tasks = load_arc_tasks()
    engine = PatternEngine(symmetry_threshold=0.90)
    
    results = []
    
    for rule in pattern_rules:
        task_id = rule['task_id']
        operator = rule.get('operator', 'N/A')
        task = all_tasks.get(task_id)
        
        if not task or not task.get('train'):
            continue
        
        # Analyze first training example
        first_example = task['train'][0]
        inp = np.array(first_example['input'])
        out = np.array(first_example['output'])
        
        # Detect symmetry in input and output
        input_sym = engine.detect_symmetry(inp)
        output_sym = engine.detect_symmetry(out)
        
        result = {
            'task_id': task_id,
            'operator': operator,
            'input_shape': inp.shape,
            'output_shape': out.shape,
            'input_best_sym': input_sym.best_axis,
            'input_sym_score': input_sym.best_score,
            'output_best_sym': output_sym.best_axis,
            'output_sym_score': output_sym.best_score,
            'input_has_any_sym': engine.has_symmetry(inp, 'any'),
            'output_has_any_sym': engine.has_symmetry(out, 'any')
        }
        results.append(result)
    
    # Print results
    print("Task Analysis:")
    print()
    for r in results:
        print(f"Task {r['task_id']} ({r['operator']}):")
        print(f"  Input:  {r['input_shape']} - {r['input_best_sym']} ({r['input_sym_score']:.3f})")
        print(f"  Output: {r['output_shape']} - {r['output_best_sym']} ({r['output_sym_score']:.3f})")
        print(f"  Input has symmetry: {r['input_has_any_sym']}")
        print(f"  Output has symmetry: {r['output_has_any_sym']}")
        print()
    
    # Statistics
    with_input_sym = sum(1 for r in results if r['input_has_any_sym'])
    with_output_sym = sum(1 for r in results if r['output_has_any_sym'])
    
    print("=" * 80)
    print("STATISTICS:")
    print(f"  Tasks with input symmetry:  {with_input_sym}/{len(results)}")
    print(f"  Tasks with output symmetry: {with_output_sym}/{len(results)}")
    print("=" * 80)
    
    return results


def test_symmetry_operators():
    """Test PATTERN-ENGINE on known symmetry operators."""
    
    print()
    print("=" * 80)
    print("TESTING SYMMETRY-BASED OPERATORS")
    print("=" * 80)
    print()
    
    # Load rules
    rules = [json.loads(line) for line in open('arc_rules_with_math_expansion.jsonl')]
    
    # Find symmetry-related operators
    symmetry_ops = [
        'symmetry_completion',
        'symmetry_from_fragment',
        'mirror',
        'diagonal_reflection'
    ]
    
    sym_rules = [r for r in rules if r.get('operator') in symmetry_ops]
    
    print(f"Found {len(sym_rules)} rules with symmetry operators:")
    for r in sym_rules:
        print(f"  - {r['task_id']}: {r['operator']}")
    print()
    
    # Load and test
    all_tasks = load_arc_tasks()
    engine = PatternEngine(symmetry_threshold=0.85)
    
    for rule in sym_rules:
        task_id = rule['task_id']
        operator = rule['operator']
        task = all_tasks.get(task_id)
        
        if not task or not task.get('train'):
            continue
        
        print(f"Task {task_id} ({operator}):")
        
        # Analyze each training example
        for i, example in enumerate(task['train']):
            inp = np.array(example['input'])
            out = np.array(example['output'])
            
            input_sym = engine.detect_symmetry(inp)
            output_sym = engine.detect_symmetry(out)
            
            print(f"  Example {i+1}:")
            print(f"    Input:  {inp.shape} - {input_sym.best_axis} ({input_sym.best_score:.2f})")
            print(f"    Output: {out.shape} - {output_sym.best_axis} ({output_sym.best_score:.2f})")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    test_pattern_engine_on_rules()
    test_symmetry_operators()
