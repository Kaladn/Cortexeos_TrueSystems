import polars as pl
import numpy as np
import os

print("="*80)
print("KAGGLE CSV FILES - DEEP INVESTIGATION")
print("="*80)

files = {
    'train.csv': 'Main training data',
    'test.csv': 'Test data for predictions',
    'train_demographics.csv': 'Training demographics/metadata',
    'test_demographics.csv': 'Test demographics/metadata'
}

for filename, description in files.items():
    filepath = f'data/kaggle/{filename}'
    if os.path.exists(filepath):
        print(f"\n{'='*80}")
        print(f"{filename} - {description}")
        print(f"{'='*80}")
        
        df = pl.read_csv(filepath)
        print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
        print(f"\nColumns ({len(df.columns)}):")
        for i, col in enumerate(df.columns):
            print(f"  {i+1:3d}. {col}")
        
        print(f"\nFirst few rows:")
        print(df.head(3))
        
        # Check for thermal/ToF data quality
        if 'thm_1' in df.columns:
            print(f"\n{'='*60}")
            print("THERMAL SENSOR ANALYSIS")
            print(f"{'='*60}")
            
            for thm_col in ['thm_1', 'thm_2', 'thm_3', 'thm_4', 'thm_5']:
                vals = df[thm_col].to_numpy()
                print(f"{thm_col}:")
                print(f"  Mean: {np.mean(vals):.3f}, Std: {np.std(vals):.3f}")
                print(f"  Min: {np.min(vals):.3f}, Max: {np.max(vals):.3f}")
                print(f"  Unique values: {len(np.unique(vals))}")
                
                # Check if constant per sequence
                if 'sequence_id' in df.columns:
                    seq_sample = df.filter(pl.col('sequence_id') == df['sequence_id'][0])
                    seq_vals = seq_sample[thm_col].to_numpy()
                    print(f"  First sequence std: {np.std(seq_vals):.3f}")
        
        if 'tof_1_v0' in df.columns:
            print(f"\n{'='*60}")
            print("TOF SENSOR ANALYSIS")
            print(f"{'='*60}")
            
            for sensor_idx in range(1, 6):
                tof_col = f'tof_{sensor_idx}_v0'
                vals = df[tof_col].to_numpy()
                print(f"{tof_col}:")
                print(f"  Mean: {np.mean(vals):.3f}, Std: {np.std(vals):.3f}")
                print(f"  Min: {np.min(vals):.3f}, Max: {np.max(vals):.3f}")
                print(f"  Unique values: {len(np.unique(vals))}")

print(f"\n{'='*80}")
print("DEMOGRAPHICS FILES - CHECK FOR HIDDEN INFO")
print(f"{'='*80}")

# Check if demographics have gesture-related info
if os.path.exists('data/kaggle/train_demographics.csv'):
    demo = pl.read_csv('data/kaggle/train_demographics.csv')
    print(f"\nTrain demographics columns: {demo.columns}")
    print(f"Shape: {demo.shape}")
    print(f"\nSample:")
    print(demo.head(5))
    
    # Check if any column correlates with gesture
    train = pl.read_csv('data/kaggle/train.csv')
    if 'sequence_id' in demo.columns and 'sequence_id' in train.columns:
        print(f"\n⚠️  Checking for data leakage in demographics...")
        
        # Get unique gestures per sequence
        gestures_per_seq = train.group_by('sequence_id').agg(pl.col('gesture').first())
        
        # Join with demographics
        merged = demo.join(gestures_per_seq, on='sequence_id', how='left')
        
        print(f"Merged shape: {merged.shape}")
        print(f"Columns: {merged.columns}")
        
        # Check if any demographic column perfectly predicts gesture
        if 'gesture' in merged.columns:
            for col in demo.columns:
                if col != 'sequence_id':
                    try:
                        unique_combos = merged.group_by([col, 'gesture']).count().shape[0]
                        total_unique_vals = merged[col].n_unique()
                        print(f"\n{col}: {unique_combos} unique (col, gesture) pairs")
                        print(f"  Unique {col} values: {total_unique_vals}")
                        
                        if unique_combos == total_unique_vals:
                            print(f"  🚨 PERFECT CORRELATION: {col} might leak gesture info!")
                    except:
                        pass

print(f"\n{'='*80}")
print("KEY FINDINGS:")
print(f"{'='*80}")
print("1. Do thermal sensors vary within sequences?")
print("2. Do ToF sensors have meaningful range?")
print("3. Do demographics leak gesture information?")
print("4. Are there any columns we're missing?")
print(f"{'='*80}")
