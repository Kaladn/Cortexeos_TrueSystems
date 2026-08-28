"""
EXPAND RULE DATABASE: Next 50 Tasks

Process:
1. Get next 50 unsolved tasks
2. Try all operators on each
3. Extract successful rules
4. Convert to mathematical notation
5. Append to arc_transformation_rules_with_math.jsonl

This iteratively builds the complete ARC mathematical rulebook.
"""
import json
import numpy as np
from pathlib import Path
from cod_616.arc_organ.arc_operators import OPERATORS
from scipy import ndimage

print("="*80)
print("📈 EXPANDING RULE DATABASE: NEXT 50 TASKS")
print("="*80)
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

# Load existing rules to avoid duplicates
existing_tasks = set()
with open('arc_transformation_rules_with_math.jsonl', 'r') as f:
    for line in f:
        rule = json.loads(line)
        existing_tasks.add(rule['task_id'])

print(f"Existing rules: {len(existing_tasks)}")
print()

# Get unsolved tasks
unsolved_tasks = [tid for tid in sorted(all_data.keys()) if tid not in existing_tasks]
print(f"Unsolved tasks: {len(unsolved_tasks)}")
print()

# Build operator dict
op_dict = {op.name: op for op in OPERATORS}

def test_operator_on_task(task_data, operator):
    """Test if operator solves all training examples."""
    try:
        for example in task_data['train']:
            inp = np.array(example['input'])
            expected = np.array(example['output'])
            
            params = operator.analyze(inp, expected)
            if params is None:
                return False
            
            result = operator.apply(inp, params)
            if not np.array_equal(result, expected):
                return False
        return True
    except:
        return False

def extract_semantic_features(inp, out):
    """Extract semantic features for math conversion."""
    features = {}
    
    # Grid properties
    features['H_in'], features['W_in'] = inp.shape
    features['H_out'], features['W_out'] = out.shape
    features['same_size'] = (inp.shape == out.shape)
    
    # Color properties
    colors_in = set(inp.flatten()) - {0}
    colors_out = set(out.flatten()) - {0}
    features['colors_in'] = len(colors_in)
    features['colors_out'] = len(colors_out)
    features['color_set_in'] = sorted(list(colors_in))
    features['color_set_out'] = sorted(list(colors_out))
    features['same_colors'] = (colors_in == colors_out)
    
    # Shape properties
    features['has_shapes'] = check_has_shapes(inp)
    if features['has_shapes']:
        features['num_shapes_in'] = count_shapes(inp)
        features['num_shapes_out'] = count_shapes(out)
        features['shapes_preserved'] = (features['num_shapes_in'] == features['num_shapes_out'])
    
    # Transform type
    if inp.shape == out.shape and np.array_equal((inp > 0), (out > 0)):
        features['transform_type'] = 'pure_recolor'
    elif inp.shape != out.shape:
        if out.shape[0] > inp.shape[0] or out.shape[1] > inp.shape[1]:
            features['transform_type'] = 'expansion'
        else:
            features['transform_type'] = 'contraction'
    else:
        features['transform_type'] = 'spatial_rearrange'
    
    # Symmetry
    features['symmetric_in'] = check_symmetry(inp)
    features['symmetric_out'] = check_symmetry(out)
    
    return features

def check_has_shapes(grid):
    nonzero = (grid > 0).astype(int)
    labeled, num = ndimage.label(nonzero)
    return num > 0

def count_shapes(grid):
    nonzero = (grid > 0).astype(int)
    labeled, num = ndimage.label(nonzero)
    return num

def check_symmetry(grid):
    h_sym = np.array_equal(grid, np.fliplr(grid))
    v_sym = np.array_equal(grid, np.flipud(grid))
    return h_sym or v_sym

# Load math definitions from previous run
with open('arc_mathematical_reference.json') as f:
    math_ref = json.load(f)

OPERATOR_MATH = {}
for op_name, op_data in math_ref['operators'].items():
    OPERATOR_MATH[op_name] = op_data

print("Scanning next 50 unsolved tasks for solvable patterns...")
print()

new_rules = []
tasks_tested = 0
target_new_rules = 50

for task_id in unsolved_tasks:
    if len(new_rules) >= target_new_rules:
        break
    
    tasks_tested += 1
    if tasks_tested % 20 == 0:
        print(f"Progress: {tasks_tested} tasks tested, {len(new_rules)} new rules found")
    
    task_data = all_data[task_id]
    
    # Try each operator
    for op_name, operator in op_dict.items():
        if test_operator_on_task(task_data, operator):
            # Found a solution!
            inp = np.array(task_data['train'][0]['input'])
            out = np.array(task_data['train'][0]['output'])
            
            features = extract_semantic_features(inp, out)
            
            # Get math definition
            math_def = OPERATOR_MATH.get(op_name, {
                'name': op_name,
                'math_type': 'undefined',
                'definitions': {},
                'formal_notation': {},
                'latex': 'Not yet defined'
            })
            
            # Build rule entry
            rule = {
                'task_id': task_id,
                'steps': 1,
                'operators': [op_name],
                'rule_description': f"Apply {op_name} operator",
                'semantic_features': features,
                'mathematical_definitions': [math_def],
                'math_rule': generate_math_rule(op_name, features, math_def),
                'examples': [{
                    'input': inp.tolist(),
                    'output': out.tolist(),
                    'input_shape': list(inp.shape),
                    'output_shape': list(out.shape)
                }]
            }
            
            new_rules.append(rule)
            print(f"  ✓ {task_id} → {op_name}")
            break

def generate_math_rule(op_name, features, math_def):
    """Generate mathematical rule specification."""
    
    # Base math rule structure
    math_rule = {
        'objects': [],
        'conditions': [],
        'equations': [],
        'transform': []
    }
    
    # Add grid definitions
    math_rule['objects'].append(
        f"G_in ∈ ℕ^({features['H_in']}×{features['W_in']})"
    )
    math_rule['objects'].append(
        f"G_out ∈ ℕ^({features['H_out']}×{features['W_out']})"
    )
    
    # Add size condition
    if features['same_size']:
        math_rule['conditions'].append(
            "Grid size preserved: H_out = H_in, W_out = W_in"
        )
    elif features['transform_type'] == 'expansion':
        math_rule['conditions'].append(
            f"Grid expands: {features['H_out']}×{features['W_out']} > {features['H_in']}×{features['W_in']}"
        )
    elif features['transform_type'] == 'contraction':
        math_rule['conditions'].append(
            f"Grid contracts: {features['H_out']}×{features['W_out']} < {features['H_in']}×{features['W_in']}"
        )
    
    # Add color conditions
    if features['same_colors']:
        math_rule['conditions'].append(
            "Color palette preserved"
        )
    
    # Add transform-specific math from definitions
    if 'definitions' in math_def:
        for key, val in math_def['definitions'].items():
            if key != 'domain':
                math_rule['equations'].append(f"{key}: {val}")
    
    if 'formal_notation' in math_def:
        for key, val in math_def['formal_notation'].items():
            if key not in ['input', 'output']:
                math_rule['transform'].append(f"{key}: {val}")
    
    return math_rule

print()
print(f"Completed scan: {tasks_tested} tasks tested")
print(f"Found {len(new_rules)} new solvable tasks")
print()

if len(new_rules) == 0:
    print("⚠️  No new solvable tasks found in next batch")
    print("   Current operators may have reached their coverage limit")
    print("   Recommendation: Develop new specialized operators")
else:
    print("="*80)
    print("💾 APPENDING NEW RULES TO DATABASE")
    print("="*80)
    print()
    
    # Append to existing JSONL
    with open('arc_transformation_rules_with_math.jsonl', 'a') as f:
        for rule in new_rules:
            f.write(json.dumps(rule) + '\n')
    
    print(f"✅ Added {len(new_rules)} new rules")
    print(f"   Total rules in database: {len(existing_tasks) + len(new_rules)}")
    print()
    
    # Statistics
    op_counts = {}
    for rule in new_rules:
        op = rule['operators'][0]
        op_counts[op] = op_counts.get(op, 0) + 1
    
    print("New rules by operator:")
    for op, count in sorted(op_counts.items(), key=lambda x: -x[1]):
        print(f"  {op}: {count}")
    print()
    
    print("="*80)
    print("📊 UPDATED DATABASE SUMMARY")
    print("="*80)
    print()
    print(f"Total solved tasks: {len(existing_tasks) + len(new_rules)}/{len(all_data)}")
    print(f"Coverage: {(len(existing_tasks) + len(new_rules)) / len(all_data) * 100:.1f}%")
    print()
    
    # Calculate transform type distribution
    transform_types = {}
    for rule in new_rules:
        ttype = rule['semantic_features']['transform_type']
        transform_types[ttype] = transform_types.get(ttype, 0) + 1
    
    print("Transform types in new rules:")
    for ttype, count in sorted(transform_types.items(), key=lambda x: -x[1]):
        print(f"  {ttype}: {count}")

print()
print("="*80)
print("✅ EXPANSION COMPLETE")
print("="*80)
print()
print("Next steps:")
print("  1. Review new mathematical rules")
print("  2. Identify patterns in unsolvable tasks")
print("  3. Design new operators for uncovered patterns")
print("  4. Iterate to expand coverage")
