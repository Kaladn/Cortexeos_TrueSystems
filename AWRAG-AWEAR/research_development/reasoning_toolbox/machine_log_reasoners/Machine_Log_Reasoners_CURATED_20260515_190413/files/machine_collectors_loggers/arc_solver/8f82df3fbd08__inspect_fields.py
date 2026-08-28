import polars as pl
import numpy as np

# Load training data
train = pl.read_csv('data/kaggle/train.csv')

print("="*80)
print("AVAILABLE COLUMNS IN DATASET")
print("="*80)
print(f"Total columns: {len(train.columns)}\n")

# Show all columns
for i, col in enumerate(train.columns, 1):
    print(f"{i:3d}. {col}")

print("\n" + "="*80)
print("COLUMNS CURRENTLY BEING USED")
print("="*80)
used_columns = ['acc_x', 'acc_y', 'acc_z', 'rot_w', 'rot_x', 'rot_y', 'rot_z']
print(f"Count: {len(used_columns)}\n")
for col in used_columns:
    print(f"  - {col}")

print("\n" + "="*80)
print("COLUMNS WE ARE NOT USING")
print("="*80)
unused = [col for col in train.columns if col not in used_columns + ['sequence_id', 'gesture']]
print(f"Count: {len(unused)}\n")

# Group unused columns by type
thermal_cols = [col for col in unused if col.startswith('thm')]
tof_cols = [col for col in unused if col.startswith('tof')]
other_cols = [col for col in unused if not col.startswith('thm') and not col.startswith('tof')]

print(f"Thermal sensors ({len(thermal_cols)}): {thermal_cols[:10]}")
print(f"ToF sensors ({len(tof_cols)}): {tof_cols[:10]}")
print(f"Other columns ({len(other_cols)}): {other_cols}")

print("\n" + "="*80)
print("SAMPLE DATA FROM UNUSED COLUMNS")
print("="*80)

# Check one sequence
seq_sample = train.filter(pl.col('sequence_id') == 'SEQ_000001')
print(f"\nSample sequence: SEQ_000001 (length: {len(seq_sample)})")
print(f"Gesture: {seq_sample['gesture'][0]}")

# Check thermal sensors
if thermal_cols:
    print(f"\nThermal sensors (first 5):")
    for col in thermal_cols[:5]:
        vals = seq_sample[col].to_numpy()
        print(f"  {col}: mean={np.mean(vals):.3f}, std={np.std(vals):.3f}, min={np.min(vals):.3f}, max={np.max(vals):.3f}")

# Check ToF sensors
if tof_cols:
    print(f"\nToF sensors (first 5):")
    for col in tof_cols[:5]:
        vals = seq_sample[col].to_numpy()
        print(f"  {col}: mean={np.mean(vals):.3f}, std={np.std(vals):.3f}, min={np.min(vals):.3f}, max={np.max(vals):.3f}")

print("\n" + "="*80)
print("FEATURE COUNT SUMMARY")
print("="*80)
print(f"Currently using: {len(used_columns)} columns")
print(f"Available but unused: {len(unused)} columns")
print(f"  - Thermal: {len(thermal_cols)}")
print(f"  - ToF: {len(tof_cols)}")
print(f"  - Other: {len(other_cols)}")
print(f"Utilization rate: {len(used_columns)}/{len(train.columns)} = {100*len(used_columns)/len(train.columns):.1f}%")
