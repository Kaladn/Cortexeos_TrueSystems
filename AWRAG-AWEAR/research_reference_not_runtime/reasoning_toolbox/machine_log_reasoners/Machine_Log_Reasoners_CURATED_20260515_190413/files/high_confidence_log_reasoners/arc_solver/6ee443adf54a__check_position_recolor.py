"""
Quick check: which tasks does position_based_recolor fully match?
"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import PositionBasedRecolorOperator, merge_operator_params

with open("arc-prize-2024/arc-agi_training_challenges.json", "r") as f:
    train_challenges = json.load(f)

op = PositionBasedRecolorOperator()
matched_tasks = []

for task_id in train_challenges.keys():
    task = train_challenges[task_id]
    train_pairs = [
        (np.array(ex["input"]), np.array(ex["output"]))
        for ex in task["train"]
    ]
    
    params_list = []
    for inp, out in train_pairs:
        p = op.analyze(inp, out)
        if p is None:
            break
        params_list.append(p)
    else:
        # All matched
        merged = merge_operator_params(op, params_list)
        if merged is not None:
            matched_tasks.append(task_id)

print(f"position_based_recolor full matches: {len(matched_tasks)}")
for tid in matched_tasks:
    print(f"  {tid}")
