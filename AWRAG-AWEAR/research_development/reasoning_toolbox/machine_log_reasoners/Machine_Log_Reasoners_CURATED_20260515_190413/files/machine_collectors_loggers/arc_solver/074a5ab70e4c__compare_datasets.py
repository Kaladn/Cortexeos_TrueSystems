"""
Compare 5 random matching tasks between Kaggle and ARC-AGI-master formats
to verify they contain identical puzzle data.
"""
import json
import numpy as np
import random
from pathlib import Path

# Tasks that appear in both datasets
matching_tasks = [
    '007bbfb7', '332efdb3', '3befdf3e', '496994bd', '5582e5ca',
    '5b6cbef5', '67a3c6ac', '68b16354', 'a416b8f3', 'b1948b0a',
    'c8f0f002', 'd511f180', 'd5d6de2d', 'f25ffba3'
]

# Pick 5 random tasks
random.seed(42)
test_tasks = random.sample(matching_tasks, 5)

print("="*70)
print("DEEP COMPARISON: Kaggle vs ARC-AGI-master")
print("Testing 5 random matching tasks for EXACT puzzle equality")
print("="*70)

# Load Kaggle format
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    kaggle_train = json.load(f)
with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    kaggle_eval = json.load(f)

kaggle_all = {**kaggle_train, **kaggle_eval}

# Load ARC-AGI-master format
master_train_dir = Path('ARC-AGI-master/data/training')
master_eval_dir = Path('ARC-AGI-master/data/evaluation')

def load_master_task(task_id):
    """Load task from ARC-AGI-master format."""
    train_path = master_train_dir / f"{task_id}.json"
    eval_path = master_eval_dir / f"{task_id}.json"
    
    if train_path.exists():
        with open(train_path, 'r') as f:
            return json.load(f)
    elif eval_path.exists():
        with open(eval_path, 'r') as f:
            return json.load(f)
    else:
        return None

def grids_equal(grid1, grid2):
    """Check if two grids are exactly equal."""
    return np.array_equal(np.array(grid1), np.array(grid2))

def compare_tasks(task_id, kaggle_task, master_task):
    """Deep comparison of task data."""
    print(f"\n{'='*70}")
    print(f"TASK: {task_id}")
    print(f"{'='*70}")
    
    # Compare training examples count
    kaggle_train_count = len(kaggle_task['train'])
    master_train_count = len(master_task['train'])
    
    print(f"\nTraining examples:")
    print(f"  Kaggle: {kaggle_train_count}")
    print(f"  Master: {master_train_count}")
    
    if kaggle_train_count != master_train_count:
        print("  ❌ MISMATCH: Different number of training examples!")
        return False
    
    # Compare each training example
    all_match = True
    for i in range(kaggle_train_count):
        k_inp = kaggle_task['train'][i]['input']
        k_out = kaggle_task['train'][i]['output']
        m_inp = master_task['train'][i]['input']
        m_out = master_task['train'][i]['output']
        
        inp_match = grids_equal(k_inp, m_inp)
        out_match = grids_equal(k_out, m_out)
        
        if inp_match and out_match:
            print(f"  Example {i+1}: ✓ IDENTICAL")
        else:
            print(f"  Example {i+1}: ❌ MISMATCH")
            if not inp_match:
                print(f"    - Input grids differ")
            if not out_match:
                print(f"    - Output grids differ")
            all_match = False
    
    # Compare test examples count
    kaggle_test_count = len(kaggle_task['test'])
    master_test_count = len(master_task['test'])
    
    print(f"\nTest examples:")
    print(f"  Kaggle: {kaggle_test_count}")
    print(f"  Master: {master_test_count}")
    
    if kaggle_test_count != master_test_count:
        print("  ❌ MISMATCH: Different number of test examples!")
        return False
    
    # Compare each test example
    for i in range(kaggle_test_count):
        k_inp = kaggle_task['test'][i]['input']
        m_inp = master_task['test'][i]['input']
        
        inp_match = grids_equal(k_inp, m_inp)
        
        # Check if outputs exist (training tasks have them, evaluation tasks don't)
        k_has_out = 'output' in kaggle_task['test'][i]
        m_has_out = 'output' in master_task['test'][i]
        
        if k_has_out and m_has_out:
            k_out = kaggle_task['test'][i]['output']
            m_out = master_task['test'][i]['output']
            out_match = grids_equal(k_out, m_out)
            
            if inp_match and out_match:
                print(f"  Test {i+1}: ✓ IDENTICAL (with output)")
            else:
                print(f"  Test {i+1}: ❌ MISMATCH")
                if not inp_match:
                    print(f"    - Input grids differ")
                if not out_match:
                    print(f"    - Output grids differ")
                all_match = False
        elif not k_has_out and not m_has_out:
            if inp_match:
                print(f"  Test {i+1}: ✓ IDENTICAL (input only)")
            else:
                print(f"  Test {i+1}: ❌ MISMATCH - Input grids differ")
                all_match = False
        else:
            print(f"  Test {i+1}: ❌ MISMATCH - Output presence differs")
            all_match = False
    
    if all_match:
        print(f"\n✅ VERDICT: Task {task_id} is IDENTICAL in both datasets")
    else:
        print(f"\n❌ VERDICT: Task {task_id} has DIFFERENCES")
    
    return all_match

# Run comparison
print(f"\nTesting tasks: {', '.join(test_tasks)}\n")

results = []
for task_id in test_tasks:
    kaggle_task = kaggle_all[task_id]
    master_task = load_master_task(task_id)
    
    if master_task is None:
        print(f"\n❌ ERROR: Could not load {task_id} from ARC-AGI-master")
        results.append(False)
        continue
    
    match = compare_tasks(task_id, kaggle_task, master_task)
    results.append(match)

# Final summary
print(f"\n{'='*70}")
print("FINAL SUMMARY")
print(f"{'='*70}")
print(f"\nTasks tested: {len(test_tasks)}")
print(f"Perfect matches: {sum(results)}")
print(f"Mismatches: {len(results) - sum(results)}")

if all(results):
    print("\n✅ CONCLUSION: All tested tasks are BYTE-FOR-BYTE IDENTICAL")
    print("   The datasets contain the exact same puzzles in different formats.")
else:
    print("\n❌ CONCLUSION: Some tasks differ between datasets")
    print("   The datasets may not be identical.")

print(f"{'='*70}\n")
