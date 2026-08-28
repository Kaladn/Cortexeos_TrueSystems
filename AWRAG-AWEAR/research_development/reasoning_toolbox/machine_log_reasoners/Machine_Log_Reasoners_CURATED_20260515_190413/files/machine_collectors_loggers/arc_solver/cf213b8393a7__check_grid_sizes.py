import json

with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['b8cdaf2b']

for i, ex in enumerate(task['train'], 1):
    inp_h = len(ex['input'])
    inp_w = len(ex['input'][0])
    out_h = len(ex['output'])
    out_w = len(ex['output'][0])
    print(f"Example {i}: Input {inp_h}x{inp_w}, Output {out_h}x{out_w}")
