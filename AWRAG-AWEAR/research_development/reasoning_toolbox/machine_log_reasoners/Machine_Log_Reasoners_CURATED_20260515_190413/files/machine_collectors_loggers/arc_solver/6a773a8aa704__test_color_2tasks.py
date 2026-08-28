from arc_core import ArcCore
import json

challenges = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
solutions = json.load(open('arc-prize-2025/arc-agi_training_solutions.json'))

core = ArcCore()
tasks = ['b1948b0a', 'c8f0f002']

print('Testing COLOR-ENGINE on 2 consistent mapping tasks:')
for tid in tasks:
    task = challenges[tid].copy()
    task['test'] = [{'input': solutions[tid][0]}]
    trace = core.solve(task, tid)
    status = "✓ SOLVED" if trace.success else "✗ FAILED"
    dsl = trace.winning_hypothesis.dsl_program if trace.winning_hypothesis else "none"
    print(f'  {tid}: {status} ({dsl})')
