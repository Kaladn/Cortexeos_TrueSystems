"""Analyze the 104 high-confidence evaluation matches."""
import json
from collections import Counter

with open('results/eval_anchor_point_matches.json') as f:
    results = json.load(f)

high = results['high_confidence']

print('ANALYSIS: 104 High-Confidence Evaluation Tasks')
print('='*70)

# Count by transform type
transforms = Counter([m[1]['transform'] for m in high])

print('\nBy Transform Type:')
for transform, count in transforms.most_common():
    print(f'  {transform}: {count} tasks')

# Count by color preservation
color_preserved = sum(1 for m in high if m[1].get('color_preserved', False))
print(f'\nColor Preserved: {color_preserved}/{len(high)} tasks ({100*color_preserved/len(high):.0f}%)')

# Check confidence == 1.0 (perfect match)
perfect = sum(1 for m in high if m[1]['confidence'] == 1.0)
print(f'Perfect confidence (1.0): {perfect}/{len(high)} tasks ({100*perfect/len(high):.0f}%)')

print('\nFirst 20 high-confidence eval tasks:')
for i, (tid, info) in enumerate(high[:20], 1):
    color_mark = 'Y' if info.get('color_preserved') else 'N'
    print(f"{i:2}. {tid}: {info['transform']:20s} conf={info['confidence']:.2f}, "
          f"obj={info['objects']}, colors={color_mark}")

print('\n' + '='*70)
print('KEY INSIGHT: These tasks have CORRECT anchor measurements')
print('but something else is changing (likely object creation/modification)')
print('='*70)
