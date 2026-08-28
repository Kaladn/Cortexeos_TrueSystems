"""Debug why specific tasks fail."""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import SelfReferentialTilingOperator, RecolorMappingOperator

# Load training data
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    train_data = json.load(f)

# Test 007bbfb7 (should be self-referential tiling)
print("="*70)
print("Testing 007bbfb7")
print("="*70)

task = train_data['007bbfb7']
ex = task['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])

print(f"Input shape: {inp.shape}")
print(f"Output shape: {out.shape}")
print(f"Expansion factor: {out.shape[0] / inp.shape[0]:.1f}x{out.shape[1] / inp.shape[1]:.1f}")

op = SelfReferentialTilingOperator()
params = op.analyze(inp, out)
print(f"SelfReferential result: {params}")

# Also test with TilingExpand
from cod_616.arc_organ.arc_operators import TilingExpandOperator
op2 = TilingExpandOperator()
params2 = op2.analyze(inp, out)
print(f"TilingExpand result: {params2}")

# Test d511f180 (should be recolor)
print(f"\n{'='*70}")
print("Testing d511f180")
print("="*70)

task = train_data['d511f180']
ex = task['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])

print(f"Input shape: {inp.shape}")
print(f"Output shape: {out.shape}")
print(f"Input unique colors: {np.unique(inp)}")
print(f"Output unique colors: {np.unique(out)}")

op3 = RecolorMappingOperator()
params3 = op3.analyze(inp, out)
print(f"RecolorMapping result: {params3}")

# Check for differences
diff_mask = (inp != out)
print(f"Differences: {diff_mask.sum()} pixels changed")
if diff_mask.sum() > 0:
    changed_inp = inp[diff_mask]
    changed_out = out[diff_mask]
    print(f"Changed from: {np.unique(changed_inp)}")
    print(f"Changed to: {np.unique(changed_out)}")
