#!/usr/bin/env python3
"""Analyze evaluation results."""

import json

with open('results/evaluation_results_20251130_174508.json') as f:
    results = json.load(f)

print("=== EVALUATION ANALYSIS ===\n")
print(f"Total: {results['total_tasks']}")
print(f"Solved: {results['solved']}")
print(f"Solve rate: {results['solve_rate']*100:.2f}%\n")

# Find solved tasks
solved_tasks = [tid for tid, res in results['results'].items() if res.get('solved')]

print(f"Solved tasks ({len(solved_tasks)}):")
for tid in solved_tasks:
    res = results['results'][tid]
    print(f"  {tid}: {res.get('engine')}/{res.get('operation')}")

print("\n=== FAILURE REASONS ===")
from collections import Counter
reasons = Counter(res.get('reason', 'unknown') for res in results['results'].values() if not res.get('solved'))
for reason, count in reasons.most_common(10):
    print(f"  {reason:30} {count:3}")
