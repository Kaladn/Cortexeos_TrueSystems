import json

# Load hybrid results (latest)
with open('results/hybrid_results_20251130_164406.json') as f:
    hybrid = json.load(f)

# Load baseline results
with open('results/solver_results_20251130_162701.json') as f:
    baseline = json.load(f)

hybrid_tasks = set(hybrid['solutions'].keys())
baseline_tasks = set(baseline['solutions'].keys())

# Find new solves
new_solves = hybrid_tasks - baseline_tasks
arc_core_solves = [tid for tid, info in hybrid['solutions'].items() if info['method'] == 'arc_core']

print("=" * 60)
print("NEW SOLVES ANALYSIS")
print("=" * 60)
print()
print(f"Baseline solves: {len(baseline_tasks)}")
print(f"Hybrid solves: {len(hybrid_tasks)}")
print(f"New solves: {len(new_solves)}")
print()

if new_solves:
    print("NEW tasks solved by hybrid:")
    for tid in sorted(new_solves):
        info = hybrid['solutions'][tid]
        if info['method'] == 'arc_core':
            print(f"  {tid}: ARC-CORE ({info['engine']}) - {info['dsl']}")
        else:
            print(f"  {tid}: Baseline ({info.get('operator', 'unknown')})")

print()
print(f"Total ARC-CORE solves: {len([t for t in arc_core_solves])}")
print(f"ARC-CORE overlap with baseline: {len(set(arc_core_solves) & baseline_tasks)}")
print(f"ARC-CORE new solves: {len(set(arc_core_solves) - baseline_tasks)}")
