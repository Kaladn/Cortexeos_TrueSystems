"""Quick stats on expanded rule database."""
import json
from collections import Counter

rules = [json.loads(line) for line in open('arc_rules_with_math_expansion.jsonl')]

print('=' * 80)
print('ARC RULE DATABASE - FULL ANALYSIS')
print('=' * 80)
print()
print(f'Total rules: {len(rules)}')
print()

# Size transformations
size_transforms = Counter()
for r in rules:
    expansion = r.get('math_expansion_slot', {})
    geo = expansion.get('geometric_properties', {})
    st = geo.get('size_transformation')
    if st:
        size_transforms[st] += 1

print('Size Transformations:')
for st, count in size_transforms.most_common():
    print(f'  {st}: {count}')
print()

# Tiling candidates
tiling_count = sum(1 for r in rules if r.get('math_expansion_slot', {}).get('geometric_properties', {}).get('tiling_candidate'))
print(f'Tiling candidates: {tiling_count}')
print()

# Color transformations
color_transforms = Counter()
for r in rules:
    expansion = r.get('math_expansion_slot', {})
    color = expansion.get('color_properties', {})
    ct = color.get('color_transformation')
    if ct:
        color_transforms[ct] += 1

print('Color Transformations:')
for ct, count in color_transforms.most_common():
    print(f'  {ct}: {count}')
print()

print('=' * 80)
