"""
Near-Miss Diagnostic for Operator System
=========================================

Shows which operators are ALMOST firing:
- Operators that pass analyze() on some examples but fail merge
- Operators that return params but can't generalize across training examples
- Tasks where multiple operators compete
- Threshold tuning opportunities

This tells us:
- Which operators need looser constraints
- Which tasks need operator composition
- Where we have low-hanging fruit
"""
import json
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional
from cod_616.arc_organ.arc_operators import OPERATORS, merge_operator_params

# Load training data
with open("arc-prize-2024/arc-agi_training_challenges.json", "r") as f:
    train_challenges = json.load(f)

print("=" * 80)
print("OPERATOR NEAR-MISS DIAGNOSTIC")
print("=" * 80)
print(f"Scanning {len(train_challenges)} training tasks...")
print(f"Testing {len(OPERATORS)} operators")
print()

# Track results per operator
operator_stats = defaultdict(lambda: {
    'full_match': 0,           # All examples match, merge succeeds
    'partial_match': 0,        # Some examples match, merge fails
    'single_example_match': 0, # Only 1 example matches
    'no_match': 0,             # No examples match
    'merge_failures': [],      # Tasks where merge failed
    'partial_tasks': [],       # Tasks with partial matches
})

# Track per-task analysis
task_analysis = {}

for task_id in train_challenges.keys():
    task = train_challenges[task_id]
    train_pairs = [
        (np.array(ex["input"]), np.array(ex["output"]))
        for ex in task["train"]
    ]
    
    num_examples = len(train_pairs)
    task_results = []
    
    for op in OPERATORS:
        # Try to analyze each training example
        params_per_example = []
        
        for inp, out in train_pairs:
            try:
                params = op.analyze(inp, out)
                params_per_example.append(params)
            except Exception as e:
                params_per_example.append(None)
        
        # Count how many succeeded
        non_none = [p for p in params_per_example if p is not None]
        num_matches = len(non_none)
        
        if num_matches == 0:
            operator_stats[op.name]['no_match'] += 1
            continue
        
        # At least one example matched - try merge
        try:
            merged = merge_operator_params(op, non_none)
        except Exception:
            merged = None
        
        if num_matches == num_examples and merged is not None:
            # Full match - this should be a solve
            operator_stats[op.name]['full_match'] += 1
            task_results.append({
                'operator': op.name,
                'status': 'full_match',
                'examples_matched': num_matches,
                'total_examples': num_examples,
                'merged_params': merged
            })
        elif num_matches == num_examples and merged is None:
            # All examples match but merge fails - NEAR MISS
            operator_stats[op.name]['partial_match'] += 1
            operator_stats[op.name]['merge_failures'].append(task_id)
            task_results.append({
                'operator': op.name,
                'status': 'merge_failure',
                'examples_matched': num_matches,
                'total_examples': num_examples,
                'params_list': non_none
            })
        elif num_matches < num_examples:
            # Partial match - some examples work
            if num_matches == 1:
                operator_stats[op.name]['single_example_match'] += 1
            else:
                operator_stats[op.name]['partial_match'] += 1
                operator_stats[op.name]['partial_tasks'].append(task_id)
            
            task_results.append({
                'operator': op.name,
                'status': 'partial',
                'examples_matched': num_matches,
                'total_examples': num_examples,
            })
    
    # Store tasks with interesting near-misses
    interesting = [r for r in task_results if r['status'] in ('merge_failure', 'partial') 
                   and r['examples_matched'] >= 2]
    if interesting:
        task_analysis[task_id] = interesting

print("\n" + "=" * 80)
print("OPERATOR STATISTICS")
print("=" * 80)

# Sort by potential (merge failures + partial matches)
operators_by_potential = sorted(
    operator_stats.items(),
    key=lambda x: x[1]['partial_match'] + x[1]['merge_failures'].__len__(),
    reverse=True
)

for op_name, stats in operators_by_potential:
    potential = stats['partial_match'] + len(stats['merge_failures'])
    if potential == 0 and stats['full_match'] == 0:
        continue  # Skip completely dormant
    
    print(f"\n{op_name}:")
    print(f"  ✅ Full matches: {stats['full_match']}")
    print(f"  ⚠️  Merge failures: {len(stats['merge_failures'])}")
    print(f"  🔶 Partial matches: {stats['partial_match']}")
    print(f"  🔹 Single example: {stats['single_example_match']}")
    print(f"  ❌ No matches: {stats['no_match']}")
    
    if stats['merge_failures']:
        print(f"     Merge failed on: {', '.join(stats['merge_failures'][:5])}")
        if len(stats['merge_failures']) > 5:
            print(f"     ... and {len(stats['merge_failures']) - 5} more")
    
    if stats['partial_tasks']:
        print(f"     Partial matches: {', '.join(stats['partial_tasks'][:5])}")
        if len(stats['partial_tasks']) > 5:
            print(f"     ... and {len(stats['partial_tasks']) - 5} more")

print("\n" + "=" * 80)
print("NEAR-MISS TASK DETAILS")
print("=" * 80)

# Show top near-miss tasks
near_miss_tasks = sorted(
    task_analysis.items(),
    key=lambda x: max(r['examples_matched'] for r in x[1]),
    reverse=True
)[:10]

for task_id, results in near_miss_tasks:
    print(f"\n{task_id}:")
    num_examples = results[0]['total_examples']
    print(f"  Training examples: {num_examples}")
    
    for result in results:
        if result['status'] == 'merge_failure':
            print(f"    ⚠️  {result['operator']}: ALL {result['examples_matched']} examples matched, but MERGE FAILED")
            # Show why merge failed
            params_list = result['params_list']
            if len(params_list) >= 2:
                print(f"       Example 1 params: {params_list[0]}")
                print(f"       Example 2 params: {params_list[1]}")
                if len(params_list) > 2:
                    print(f"       ... and {len(params_list) - 2} more")
        elif result['status'] == 'partial':
            print(f"    🔶 {result['operator']}: {result['examples_matched']}/{result['total_examples']} examples matched")

print("\n" + "=" * 80)
print("LOW-HANGING FRUIT ANALYSIS")
print("=" * 80)

# Find operators with many merge failures (threshold tuning opportunity)
high_merge_failures = [
    (op_name, len(stats['merge_failures']))
    for op_name, stats in operator_stats.items()
    if len(stats['merge_failures']) >= 2
]

if high_merge_failures:
    print("\n🎯 Operators with merge failures (threshold tuning needed):")
    for op_name, count in sorted(high_merge_failures, key=lambda x: x[1], reverse=True):
        print(f"   {op_name}: {count} tasks")
        print(f"      → Check merge_operator_params() logic for this operator type")
else:
    print("\n✅ No operators with significant merge failures")

# Find operators with many partial matches (composition opportunity)
high_partial = [
    (op_name, stats['partial_match'])
    for op_name, stats in operator_stats.items()
    if stats['partial_match'] >= 3
]

if high_partial:
    print("\n🔗 Operators with partial matches (composition needed):")
    for op_name, count in sorted(high_partial, key=lambda x: x[1], reverse=True):
        print(f"   {op_name}: {count} tasks")
        print(f"      → These tasks likely need multi-step transformations")
else:
    print("\n✅ No operators with significant partial matches")

# Completely dormant operators
dormant = [
    op_name for op_name, stats in operator_stats.items()
    if stats['full_match'] == 0 
    and stats['partial_match'] == 0 
    and len(stats['merge_failures']) == 0
    and stats['single_example_match'] == 0
]

if dormant:
    print(f"\n💤 Completely dormant operators ({len(dormant)}):")
    for op_name in dormant:
        print(f"   {op_name}")
        print(f"      → Either too specific, or waiting for rare task families")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nOperators with full matches: {sum(1 for s in operator_stats.values() if s['full_match'] > 0)}")
print(f"Operators with merge failures: {len(high_merge_failures)}")
print(f"Operators with partial matches: {len(high_partial)}")
print(f"Completely dormant operators: {len(dormant)}")
print(f"\nTotal near-miss tasks identified: {len(task_analysis)}")
print(f"Potential quick wins (merge failures): {sum(len(s['merge_failures']) for s in operator_stats.values())}")
