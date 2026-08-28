"""
NEXT SESSION KICKOFF — Validate System Ready

Before starting work:
1. Verify baseline state
2. Confirm all files in place
3. Check operator status
4. Display work queue

Run this at start of next session to orient yourself.
"""
import json
import os
import sys

print("="*80)
print("🔥 NEXT SESSION KICKOFF — Option B: Fix + Focused Expansion")
print("="*80)
print()

# Check baseline
print("📊 CURRENT STATE")
print("-"*80)

# Check solution files
baseline_file = 'solutions_baseline_17_operators.json'
current_file = 'solutions_with_new_operators.json'

if os.path.exists(baseline_file):
    with open(baseline_file) as f:
        baseline = json.load(f)
    print(f"✓ Baseline: {len(baseline)} solves (17 operators)")
else:
    print(f"✗ Baseline file missing: {baseline_file}")
    baseline = {}

if os.path.exists(current_file):
    with open(current_file) as f:
        current = json.load(f)
    print(f"✓ Current: {len(current)} solves (29 operators)")
else:
    print(f"✗ Current file missing: {current_file}")
    current = {}

if baseline and current:
    improvement = len(current) - len(baseline)
    pct = (improvement / len(baseline) * 100) if baseline else 0
    print(f"✓ Improvement: +{improvement} solves (+{pct:.1f}%)")

print()

# Check operator files
print("🛠️ OPERATOR STATUS")
print("-"*80)

operators_to_debug = [
    'checkerboard_tiling_alternating',
    'symmetry_from_fragment',
    'pattern_completion_prototype'
]

operators_to_add = [
    'gravity_fall',
    'object_replication',
    'line_detector'
]

print("NEED DEBUGGING (3):")
for op in operators_to_debug:
    op_file = f'cod_616/arc_organ/operators/{op}.py'
    if os.path.exists(op_file):
        print(f"  ✓ {op} (file exists, needs fix)")
    else:
        print(f"  ✗ {op} (FILE MISSING!)")

print()
print("TO BE IMPLEMENTED (3):")
for op in operators_to_add:
    op_file = f'cod_616/arc_organ/operators/{op}.py'
    if os.path.exists(op_file):
        print(f"  ✓ {op} (already exists)")
    else:
        print(f"  ⚪ {op} (not yet created)")

print()

# Check debug scripts
print("🔬 DEBUG INFRASTRUCTURE")
print("-"*80)

debug_scripts = [
    'debug_checkerboard_tiling.py',
    'debug_symmetry_from_fragment.py',
    'debug_pattern_completion.py'
]

for script in debug_scripts:
    if os.path.exists(script):
        print(f"  ✓ {script}")
    else:
        print(f"  ✗ {script} (MISSING!)")

print()

# Check math DSL specs
print("📚 MATHEMATICAL SPECIFICATIONS")
print("-"*80)

dsl_files = [
    'arc_transformation_rules_math_dsl.jsonl',
    'manual_math_dsl_complete.jsonl',
    'PHASE_2_THREE_OPERATORS_MATH_DSL.md'
]

for dsl_file in dsl_files:
    if os.path.exists(dsl_file):
        print(f"  ✓ {dsl_file}")
        if dsl_file.endswith('.jsonl'):
            with open(dsl_file) as f:
                lines = f.readlines()
            print(f"      ({len(lines)} rules)")
    else:
        print(f"  ✗ {dsl_file} (MISSING!)")

print()

# Check playbook
print("📋 PLAYBOOK")
print("-"*80)

if os.path.exists('NEXT_SESSION_PLAYBOOK.md'):
    print("  ✓ NEXT_SESSION_PLAYBOOK.md")
    print("      Full execution plan ready")
else:
    print("  ✗ NEXT_SESSION_PLAYBOOK.md (MISSING!)")

print()

# Work queue
print("="*80)
print("🎯 WORK QUEUE — PHASE 1: DEBUG (1-2 hours)")
print("="*80)
print()

print("1️⃣ Fix checkerboard_tiling_alternating")
print("   Task: 00576224 (2×2 tile → 6×6 with alternating flips)")
print("   Run: python debug_checkerboard_tiling.py")
print("   Fix: Check tile detection, flip logic, placement")
print()

print("2️⃣ Fix symmetry_from_fragment")
print("   Task: 017c7c7b (partial → complete symmetric)")
print("   Run: python debug_symmetry_from_fragment.py")
print("   Fix: Fragment detection, symmetry inference")
print()

print("3️⃣ Fix pattern_completion_prototype")
print("   Task: 00dbd492 (complete partial shapes)")
print("   Run: python debug_pattern_completion.py")
print("   Fix: Prototype ID, partial detection, alignment")
print()

print("After each fix:")
print("  → python test_new_operators.py")
print("  → python full_scan_new_operators.py")
print("  → Check for +solves, no regression")
print()

print("="*80)
print("🔥 WORK QUEUE — PHASE 2: NEW OPERATORS (2-3 hours)")
print("="*80)
print()

print("1️⃣ Implement gravity_fall")
print("   Spec: PHASE_2_THREE_OPERATORS_MATH_DSL.md")
print("   Algorithm: Column compression to bottom")
print("   Expected: +2-3 solves")
print()

print("2️⃣ Implement object_replication")
print("   Spec: PHASE_2_THREE_OPERATORS_MATH_DSL.md")
print("   Algorithm: Stamp prototype at markers")
print("   Expected: +1-2 solves")
print()

print("3️⃣ Implement line_detector")
print("   Spec: PHASE_2_THREE_OPERATORS_MATH_DSL.md")
print("   Algorithm: Detect complete H/V lines")
print("   Expected: +0-1 solves (enables composition)")
print()

print("After implementation:")
print("  → Update cod_616/arc_organ/arc_operators.py")
print("  → python full_scan_new_operators.py")
print("  → python identify_new_solves.py")
print()

print("="*80)
print("🎯 SUCCESS TARGETS")
print("="*80)
print()

print("Phase 1 (Debug):")
print("  Current: 56 solves")
print("  Target: 58-60 solves (+2-4)")
print("  Operators: 29 total, 21-22 working")
print()

print("Phase 2 (New):")
print("  Starting: 58-60 solves")
print("  Target: 63-65 solves (+3-5)")
print("  Operators: 32 total, 24-25 working")
print()

print("Combined:")
print("  🎯 TOTAL TARGET: 63-65 solves (6.3-6.5%)")
print("  🎯 WORKING OPERATORS: 24-25/32")
print("  🎯 TIME ESTIMATE: 3-5 hours")
print()

print("="*80)
print("✅ SYSTEM READY")
print("="*80)
print()

# Final checks
all_ready = True

if not os.path.exists(baseline_file):
    print("⚠️  WARNING: Baseline file missing")
    all_ready = False

if not os.path.exists(current_file):
    print("⚠️  WARNING: Current solutions file missing")
    all_ready = False

for script in debug_scripts:
    if not os.path.exists(script):
        print(f"⚠️  WARNING: {script} missing")
        all_ready = False

if not os.path.exists('NEXT_SESSION_PLAYBOOK.md'):
    print("⚠️  WARNING: Playbook missing")
    all_ready = False

if all_ready:
    print("🔥 ALL SYSTEMS GO")
    print()
    print("RECOMMENDED NEXT COMMAND:")
    print("  python debug_checkerboard_tiling.py")
    print()
    print("Then follow NEXT_SESSION_PLAYBOOK.md")
else:
    print("⚠️  SOME FILES MISSING - Review setup")

print()
print("="*80)
print(f"Generated: {os.path.basename(__file__)}")
print("Ready to execute Option B: Fix + Focused Expansion")
print("="*80)
