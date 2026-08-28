import polars as pl
import numpy as np

train = pl.read_csv('data/kaggle/train.csv')

# Check one sequence
seq = train.filter(pl.col('sequence_id') == 'SEQ_000001')
print(f"Sequence length: {len(seq)}")
print(f"Gesture: {seq['gesture'][0]}")

print("\n" + "="*60)
print("THERMAL SENSOR DATA")
print("="*60)
for col in ['thm_1', 'thm_2', 'thm_3', 'thm_4', 'thm_5']:
    vals = seq[col].to_numpy()
    print(f"{col}: mean={np.mean(vals):.3f}, std={np.std(vals):.3f}, min={np.min(vals):.3f}, max={np.max(vals):.3f}")

print("\n" + "="*60)
print("TOF SENSOR DATA (v0 from each sensor)")
print("="*60)
for i in range(1, 6):
    col = f'tof_{i}_v0'
    vals = seq[col].to_numpy()
    print(f"{col}: mean={np.mean(vals):.3f}, std={np.std(vals):.3f}, min={np.min(vals):.3f}, max={np.max(vals):.3f}")

print("\n" + "="*60)
print("IMU DATA (for comparison)")
print("="*60)
for col in ['acc_x', 'acc_y', 'acc_z']:
    vals = seq[col].to_numpy()
    print(f"{col}: mean={np.mean(vals):.3f}, std={np.std(vals):.3f}")

# Check if thermal/ToF are all zeros or have variation
print("\n" + "="*60)
print("DATA QUALITY CHECK")
print("="*60)

thermal_cols = ['thm_1', 'thm_2', 'thm_3', 'thm_4', 'thm_5']
tof_cols = [f'tof_{i}_v0' for i in range(1, 6)]

thermal_all_same = []
for col in thermal_cols:
    vals = seq[col].to_numpy()
    if np.std(vals) == 0:
        thermal_all_same.append(col)

tof_all_same = []
for col in tof_cols:
    vals = seq[col].to_numpy()
    if np.std(vals) == 0:
        tof_all_same.append(col)

if thermal_all_same:
    print(f"⚠️  Thermal sensors with ZERO variation: {thermal_all_same}")
else:
    print("✓ All thermal sensors have variation")

if tof_all_same:
    print(f"⚠️  ToF sensors with ZERO variation: {tof_all_same}")
else:
    print("✓ All ToF sensors have variation")

# Check multiple sequences
print("\n" + "="*60)
print("CHECKING 10 RANDOM SEQUENCES")
print("="*60)

seq_ids = train.select('sequence_id').unique().to_series().to_list()[:10]

for seq_id in seq_ids:
    seq = train.filter(pl.col('sequence_id') == seq_id)
    
    # Check thermal variation
    thermal_var = sum([np.std(seq[col].to_numpy()) for col in thermal_cols])
    tof_var = sum([np.std(seq[f'tof_{i}_v0'].to_numpy()) for i in range(1, 6)])
    
    print(f"{seq_id}: thermal_var={thermal_var:.3f}, tof_var={tof_var:.3f}")

print("\n" + "="*60)
print("DIAGNOSIS")
print("="*60)
print("If thermal/ToF have zero or near-zero variation across sequences:")
print("  → These sensors are useless, adding them creates noise")
print("  → Model gets confused by constant/random values")
print("  → Need to filter out bad sensors or normalize differently")
