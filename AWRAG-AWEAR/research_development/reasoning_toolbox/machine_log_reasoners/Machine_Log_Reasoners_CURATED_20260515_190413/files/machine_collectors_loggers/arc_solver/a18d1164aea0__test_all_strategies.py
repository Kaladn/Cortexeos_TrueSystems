"""Test ALL diagonal extraction strategies to find which one works."""
import json, numpy as np

c = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
s = json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
t = c['05269061']

print("="*80)
print("TESTING ALL DIAGONAL STRATEGIES")
print("="*80)

for i, ex in enumerate(t['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\n{'='*80}")
    print(f"TRAINING {i+1}")
    print(f"{'='*80}")
    
    # Extract diagonal map
    dm = {}
    for r in range(7):
        for c in range(7):
            if inp[r,c] != 0:
                d = r+c
                if d not in dm:
                    dm[d] = []
                dm[d].append(int(inp[r,c]))
    
    keys = sorted(dm.keys())[:3]
    pal = [dm[k][0] for k in keys]
    off = keys[0]
    exp = [int(x) for x in out[0,:3]]
    
    print(f"Diagonals found: {keys}")
    print(f"Offset: {off}")
    print(f"Palette extracted: {pal}")
    print(f"Expected output:   {exp}")
    
    # Test strategy 1: palette[(r+c) % 3]
    gen1 = np.array([[pal[(r+c) % 3] for c in range(7)] for r in range(7)])
    match1 = np.array_equal(gen1, out)
    print(f"\nStrategy 1: palette[(r+c) % 3]")
    print(f"  Match: {'✅' if match1 else '❌'}")
    if match1:
        print(f"  ★★★ THIS WORKS ★★★")
    
    # Test strategy 2: palette[(r+c - offset) % 3]
    gen2 = np.array([[pal[(r+c - off) % 3] for c in range(7)] for r in range(7)])
    match2 = np.array_equal(gen2, out)
    print(f"\nStrategy 2: palette[(r+c - {off}) % 3]")
    print(f"  Match: {'✅' if match2 else '❌'}")
    if match2:
        print(f"  ★★★ THIS WORKS ★★★")
    
    # Test strategy 3: Direct palette (no offset)
    if keys == [0, 1, 2]:
        gen3 = gen1
        match3 = match1
    else:
        match3 = False
    print(f"\nStrategy 3: Only works if diagonals are [0,1,2]")
    print(f"  Match: {'✅' if match3 else '❌'}")
    
    if not (match1 or match2 or match3):
        print(f"\n⚠️  NONE OF THE STRATEGIES WORK!")
        print(f"First 3x3 generated (strategy 1):")
        print(gen1[:3,:3])
        print(f"First 3x3 actual:")
        print(out[:3,:3])
        print(f"First 3x3 generated (strategy 2):")
        print(gen2[:3,:3])

# Test example
print(f"\n{'='*80}")
print(f"TEST EXAMPLE")
print(f"{'='*80}")

inp = np.array(t['test'][0]['input'])
out = np.array(s['05269061'][0])

dm = {}
for r in range(7):
    for c in range(7):
        if inp[r,c] != 0:
            d = r+c
            if d not in dm:
                dm[d] = []
            dm[d].append(int(inp[r,c]))

keys = sorted(dm.keys())[:3]
pal = [dm[k][0] for k in keys]
off = keys[0]
exp = [int(x) for x in out[0,:3]]

print(f"Diagonals found: {keys}")
print(f"Offset: {off}")
print(f"Palette extracted: {pal}")
print(f"Expected output:   {exp}")

gen1 = np.array([[pal[(r+c) % 3] for c in range(7)] for r in range(7)])
match1 = np.array_equal(gen1, out)
print(f"\nStrategy 1: palette[(r+c) % 3] - Match: {'✅' if match1 else '❌'}")

gen2 = np.array([[pal[(r+c - off) % 3] for c in range(7)] for r in range(7)])
match2 = np.array_equal(gen2, out)
print(f"Strategy 2: palette[(r+c - {off}) % 3] - Match: {'✅' if match2 else '❌'}")

print("\n" + "="*80)
print("FINAL ANSWER: Which strategy works universally?")
print("="*80)
