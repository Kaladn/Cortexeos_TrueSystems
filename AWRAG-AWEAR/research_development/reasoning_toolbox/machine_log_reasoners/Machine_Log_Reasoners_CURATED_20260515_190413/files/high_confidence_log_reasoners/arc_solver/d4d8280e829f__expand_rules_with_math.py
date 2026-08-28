"""
Expand rule database with mathematical properties and DSL features.
Prepare for PATTERN-ENGINE, GEO-ENGINE, COLOR-ENGINE integration.
"""
import json
import numpy as np
from pathlib import Path
from collections import Counter

def analyze_task_math_properties(task_data):
    """Extract mathematical properties from a task."""
    train_examples = task_data.get('train', [])
    if not train_examples:
        return {}
    
    # Analyze first training example
    first = train_examples[0]
    inp = np.array(first['input'])
    out = np.array(first['output'])
    
    properties = {}
    
    # Size properties
    properties['input_shape'] = [int(x) for x in inp.shape]
    properties['output_shape'] = [int(x) for x in out.shape]
    properties['size_ratio'] = [
        float(out.shape[0] / inp.shape[0]) if inp.shape[0] > 0 else 1.0,
        float(out.shape[1] / inp.shape[1]) if inp.shape[1] > 0 else 1.0
    ]
    properties['size_change'] = 'expansion' if np.prod(out.shape) > np.prod(inp.shape) else \
                                'reduction' if np.prod(out.shape) < np.prod(inp.shape) else 'same'
    
    # Color properties
    input_colors = set(int(x) for x in inp.flatten())
    output_colors = set(int(x) for x in out.flatten())
    properties['num_input_colors'] = len(input_colors)
    properties['num_output_colors'] = len(output_colors)
    properties['color_change'] = 'increased' if len(output_colors) > len(input_colors) else \
                                 'decreased' if len(output_colors) < len(input_colors) else 'same'
    properties['new_colors'] = sorted(list(output_colors - input_colors))
    properties['removed_colors'] = sorted(list(input_colors - output_colors))
    
    # Background detection (most common color)
    input_bg = int(Counter(inp.flatten()).most_common(1)[0][0])
    output_bg = int(Counter(out.flatten()).most_common(1)[0][0])
    properties['input_background'] = input_bg
    properties['output_background'] = output_bg
    properties['background_preserved'] = bool(input_bg == output_bg)
    
    # Symmetry detection
    properties['input_h_symmetric'] = bool(np.array_equal(inp, np.fliplr(inp)))
    properties['input_v_symmetric'] = bool(np.array_equal(inp, np.flipud(inp)))
    properties['output_h_symmetric'] = bool(np.array_equal(out, np.fliplr(out)))
    properties['output_v_symmetric'] = bool(np.array_equal(out, np.flipud(out)))
    
    # Periodicity hints (check if output is multiple of input)
    if inp.shape[0] > 0 and inp.shape[1] > 0:
        h_multiple = out.shape[0] % inp.shape[0] == 0
        w_multiple = out.shape[1] % inp.shape[1] == 0
        properties['output_is_tiling_candidate'] = h_multiple and w_multiple
        if h_multiple and w_multiple:
            properties['tiling_factor'] = [
                int(out.shape[0] // inp.shape[0]),
                int(out.shape[1] // inp.shape[1])
            ]
    else:
        properties['output_is_tiling_candidate'] = False
    
    # Object count (rough estimate: connected components of non-background)
    input_foreground = inp != input_bg
    output_foreground = out != output_bg
    properties['input_has_foreground'] = bool(input_foreground.any())
    properties['output_has_foreground'] = bool(output_foreground.any())
    
    # Grid pattern detection (checkerboard, stripes)
    properties['possible_checkerboard'] = detect_checkerboard_pattern(out)
    properties['possible_stripe_pattern'] = detect_stripe_pattern(out)
    
    return properties

def detect_checkerboard_pattern(grid):
    """Check if grid has checkerboard-like pattern."""
    if grid.shape[0] < 2 or grid.shape[1] < 2:
        return False
    
    # Simple checkerboard: (i+j) mod 2 determines color
    try:
        h, w = grid.shape
        colors = list(set(grid.flatten()))
        if len(colors) != 2:
            return False
        
        # Check if pattern matches (i+j) mod 2
        pattern_match = 0
        for i in range(h):
            for j in range(w):
                expected_parity = (i + j) % 2
                if (grid[i, j] == colors[expected_parity]):
                    pattern_match += 1
        
        match_ratio = pattern_match / (h * w)
        return match_ratio > 0.9
    except:
        return False

def detect_stripe_pattern(grid):
    """Check if grid has horizontal or vertical stripe pattern."""
    h, w = grid.shape
    
    # Horizontal stripes: each row is uniform
    h_stripe = all(len(set(row)) == 1 for row in grid)
    
    # Vertical stripes: each column is uniform
    v_stripe = all(len(set(col)) == 1 for col in grid.T)
    
    if h_stripe:
        return 'horizontal'
    elif v_stripe:
        return 'vertical'
    else:
        return None

def expand_rule_with_math(rule, all_tasks):
    """Expand a single rule with mathematical properties."""
    task_id = rule['task_id']
    task_data = all_tasks.get(task_id)
    
    if not task_data:
        return rule
    
    # Extract math properties
    math_props = analyze_task_math_properties(task_data)
    
    # Build DSL-ready expansion
    expansion = {
        'geometric_properties': {
            'size_transformation': math_props.get('size_change'),
            'size_ratio': math_props.get('size_ratio'),
            'tiling_candidate': math_props.get('output_is_tiling_candidate', False),
            'tiling_factor': math_props.get('tiling_factor')
        },
        'color_properties': {
            'color_transformation': math_props.get('color_change'),
            'num_colors_in': math_props.get('num_input_colors'),
            'num_colors_out': math_props.get('num_output_colors'),
            'background_preserved': math_props.get('background_preserved'),
            'new_colors': math_props.get('new_colors', []),
            'removed_colors': math_props.get('removed_colors', [])
        },
        'pattern_properties': {
            'input_symmetric': {
                'horizontal': math_props.get('input_h_symmetric', False),
                'vertical': math_props.get('input_v_symmetric', False)
            },
            'output_symmetric': {
                'horizontal': math_props.get('output_h_symmetric', False),
                'vertical': math_props.get('output_v_symmetric', False)
            },
            'checkerboard': math_props.get('possible_checkerboard', False),
            'stripe_pattern': math_props.get('possible_stripe_pattern')
        },
        'dsl_formula': None,  # Ready for PATTERN-ENGINE formulas
        'engine_hints': []     # Which engines should handle this
    }
    
    # Add engine hints based on operator
    if rule['rule_type'] == 'single_operator':
        op = rule['operator']
        if 'recolor' in op or 'color' in op or 'mapping' in op:
            expansion['engine_hints'].append('COLOR-ENGINE')
        if 'mirror' in op or 'crop' in op or 'center' in op:
            expansion['engine_hints'].append('GEO-ENGINE')
        if 'tiling' in op or 'symmetry' in op or 'repeat' in op:
            expansion['engine_hints'].append('PATTERN-ENGINE')
        if 'expand' in op or 'grow' in op or 'blob' in op:
            expansion['engine_hints'].append('SHAPE-ENGINE')
    
    rule['math_expansion_slot'] = expansion
    return rule

def main():
    """Expand all rules with mathematical properties."""
    
    # Load rule database
    rules = []
    with open('arc_complete_rule_database.jsonl') as f:
        rules = [json.loads(line) for line in f]
    
    # Load task data
    train_data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
    eval_data = json.load(open('arc-prize-2025/arc-agi_evaluation_challenges.json'))
    all_tasks = {**train_data, **eval_data}
    
    print("=" * 80)
    print("EXPANDING RULES WITH MATHEMATICAL PROPERTIES")
    print("=" * 80)
    print()
    print(f"Processing {len(rules)} rules...")
    print()
    
    # Expand each rule
    expanded_rules = []
    for i, rule in enumerate(rules):
        expanded = expand_rule_with_math(rule, all_tasks)
        expanded_rules.append(expanded)
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(rules)} rules...")
    
    # Save expanded database
    output_path = Path('arc_rules_with_math_expansion.jsonl')
    with open(output_path, 'w') as f:
        for rule in expanded_rules:
            f.write(json.dumps(rule) + '\n')
    
    print()
    print(f"✓ Saved expanded rules to: {output_path}")
    print()
    
    # Statistics
    engine_counts = Counter()
    for rule in expanded_rules:
        expansion = rule.get('math_expansion_slot', {})
        hints = expansion.get('engine_hints', [])
        for hint in hints:
            engine_counts[hint] += 1
    
    print("Engine Distribution:")
    for engine, count in engine_counts.most_common():
        print(f"  {engine}: {count} rules")
    print()
    
    # Show sample expanded rule
    print("=" * 80)
    print("SAMPLE EXPANDED RULE:")
    print("=" * 80)
    sample = expanded_rules[0]
    print(json.dumps(sample, indent=2))
    print()
    print("=" * 80)
    print("MATH EXPANSION COMPLETE - READY FOR ENGINE INTEGRATION")
    print("=" * 80)

if __name__ == "__main__":
    main()
