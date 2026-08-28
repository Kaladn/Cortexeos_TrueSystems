#!/usr/bin/env python3
"""Analyze which COLOR tasks were solved."""

import json
from pathlib import Path

# Load latest hybrid results
results_dir = Path("results")
latest = sorted(results_dir.glob("hybrid_results_*.json"))[-1]

with open(latest) as f:
    results = json.load(f)

# Find COLOR solves
color_solves = []
for task_id, solution in results['solutions'].items():
    if solution['solver'] == 'ARC-CORE':
        trace = solution.get('trace', {})
        if trace.get('engine') == 'COLOR':
            color_solves.append({
                'task_id': task_id,
                'operation': trace.get('operation', '?'),
                'confidence': trace.get('confidence', 0),
                'dsl': trace.get('dsl_program', ''),
                'explanation': trace.get('explanation', '')
            })

print(f"\n=== COLOR-ENGINE SOLVES ({len(color_solves)}) ===\n")

for solve in sorted(color_solves, key=lambda x: x['operation']):
    print(f"{solve['task_id']}: {solve['operation']}")
    print(f"  DSL: {solve['dsl']}")
    print(f"  Confidence: {solve['confidence']:.2f}")
    print()
