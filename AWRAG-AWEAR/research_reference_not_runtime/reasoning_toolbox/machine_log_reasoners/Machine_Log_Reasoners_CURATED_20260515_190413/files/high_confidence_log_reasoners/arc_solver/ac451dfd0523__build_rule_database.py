"""
Build comprehensive rule database from all solved tasks.
Extract operator chains and prepare for math expansion.
"""
import json
from pathlib import Path

def build_rule_database():
    """Extract all solved tasks into comprehensive JSONL rule database."""
    
    # Load results
    results_path = Path('results/solver_results_20251130_152708.json')
    results = json.load(open(results_path))
    
    # Load task data for context
    train_data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
    eval_data = json.load(open('arc-prize-2025/arc-agi_evaluation_challenges.json'))
    all_tasks = {**train_data, **eval_data}
    
    # Build comprehensive rule database
    rules = []
    rule_id = 1
    
    for task_id, solution in results['solutions'].items():
        task = all_tasks.get(task_id, {})
        train_examples = task.get('train', [])
        
        # Extract grid size from first training example
        if train_examples:
            input_h = len(train_examples[0]['input'])
            input_w = len(train_examples[0]['input'][0]) if input_h > 0 else 0
            output_h = len(train_examples[0]['output'])
            output_w = len(train_examples[0]['output'][0]) if output_h > 0 else 0
            grid_info = {
                'input': [input_h, input_w],
                'output': [output_h, output_w]
            }
        else:
            grid_info = None
        
        if solution['rule_type'] == 'single':
            # Single operator rule
            rule = {
                'id': rule_id,
                'task_id': task_id,
                'rule_type': 'single_operator',
                'operator': solution['operator'],
                'config': str(solution.get('config', 'N/A')),
                'grid_size': grid_info,
                'num_train_examples': len(train_examples),
                'math_expansion_slot': None,
                'notes': f"Solved by {solution['operator']}"
            }
            rules.append(rule)
            rule_id += 1
            
        elif solution['rule_type'] == 'composition':
            # Multi-step composition
            ops = solution['operators']
            configs = solution.get('configs', {})
            
            rule = {
                'id': rule_id,
                'task_id': task_id,
                'rule_type': 'composition',
                'operator_chain': ops,
                'chain_length': len(ops),
                'operator_configs': {k: str(v) for k, v in configs.items()},
                'grid_size': grid_info,
                'num_train_examples': len(train_examples),
                'math_expansion_slot': None,
                'notes': f"Composition: {' → '.join(ops)}"
            }
            rules.append(rule)
            rule_id += 1
    
    # Write to JSONL
    output_path = Path('arc_complete_rule_database.jsonl')
    with open(output_path, 'w') as f:
        for rule in rules:
            f.write(json.dumps(rule) + '\n')
    
    # Generate statistics
    single_count = sum(1 for r in rules if r['rule_type'] == 'single_operator')
    comp_count = sum(1 for r in rules if r['rule_type'] == 'composition')
    
    print("=" * 80)
    print("ARC COMPLETE RULE DATABASE")
    print("=" * 80)
    print()
    print(f"✓ Extracted {len(rules)} rules from {len(results['solutions'])} solved tasks")
    print()
    print("Rule Breakdown:")
    print(f"  Single operators:  {single_count}")
    print(f"  Compositions:      {comp_count}")
    print()
    print(f"Database saved to: {output_path}")
    print()
    print("Math Expansion Slots:")
    print("  - Each rule has 'math_expansion_slot' field ready for DSL formulas")
    print("  - Add geometric properties, color patterns, symmetry features")
    print("  - Link to PATTERN-ENGINE, GEO-ENGINE, COLOR-ENGINE")
    print()
    
    # Show operator distribution
    from collections import Counter
    op_counts = Counter()
    for rule in rules:
        if rule['rule_type'] == 'single_operator':
            op_counts[rule['operator']] += 1
    
    print("Top Operators:")
    for op, count in op_counts.most_common(10):
        print(f"  {op}: {count}")
    print()
    
    print("=" * 80)
    print("READY FOR MATH EXPANSION")
    print("=" * 80)

if __name__ == "__main__":
    build_rule_database()
