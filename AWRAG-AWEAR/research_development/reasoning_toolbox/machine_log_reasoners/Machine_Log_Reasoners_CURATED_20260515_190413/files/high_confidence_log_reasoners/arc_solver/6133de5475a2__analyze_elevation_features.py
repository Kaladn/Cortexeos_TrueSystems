"""
Elevation & Motion Analysis - Finding Missing Features
Analyzes why we're missing high/low elevation gestures
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("ELEVATION & MOTION FEATURE ANALYSIS")
print("=" * 80)

# Load data
train = pd.read_csv('data/kaggle/train.csv')

# Define gesture groups by elevation
high_elevation = [
    'Above ear - pull hair',
    'Eyebrow - pull hair', 
    'Eyelash - pull hair',
    'Forehead - scratch',
    'Forehead - pull hairline'
]

mid_elevation = [
    'Cheek - pinch skin',
    'Glasses on/off',
    'Text on phone',
    'Wave hello',
    'Pull air toward your face'
]

low_elevation = [
    'Scratch knee/leg skin',
    'Pinch knee/leg skin',
    'Write name on leg'
]

neck_elevation = [
    'Neck - scratch',
    'Neck - pinch skin'
]

# Analyze each gesture
print("\n[HIGH ELEVATION GESTURES - Head/Face]")
print("-" * 80)
for gesture in high_elevation:
    data = train[train['gesture'] == gesture]
    print(f"\n{gesture}:")
    print(f"  Samples: {len(data)}")
    print(f"  acc_y (vertical):  mean={data['acc_y'].mean():7.3f}, std={data['acc_y'].std():6.3f}")
    print(f"  acc_z (forward):   mean={data['acc_z'].mean():7.3f}, std={data['acc_z'].std():6.3f}")
    print(f"  rot_x (pitch):     mean={data['rot_x'].mean():7.3f}, std={data['rot_x'].std():6.3f}")
    print(f"  rot_y (yaw):       mean={data['rot_y'].mean():7.3f}, std={data['rot_y'].std():6.3f}")

print("\n[LOW ELEVATION GESTURES - Knee/Leg]")
print("-" * 80)
for gesture in low_elevation:
    data = train[train['gesture'] == gesture]
    print(f"\n{gesture}:")
    print(f"  Samples: {len(data)}")
    print(f"  acc_y (vertical):  mean={data['acc_y'].mean():7.3f}, std={data['acc_y'].std():6.3f}")
    print(f"  acc_z (forward):   mean={data['acc_z'].mean():7.3f}, std={data['acc_z'].std():6.3f}")
    print(f"  rot_x (pitch):     mean={data['rot_x'].mean():7.3f}, std={data['rot_x'].std():6.3f}")
    print(f"  rot_y (yaw):       mean={data['rot_y'].mean():7.3f}, std={data['rot_y'].std():6.3f}")

# Current features vs missing features
print("\n" + "=" * 80)
print("FEATURE ENGINEERING GAPS")
print("=" * 80)

print("\n[CURRENT FEATURES - What we extract now]")
print("  1. acc_x/y/z mean, std, max, min (12 features)")
print("  ❌ Missing: No rotation/gyro features!")
print("  ❌ Missing: No elevation indicators!")
print("  ❌ Missing: No gesture height classification!")

print("\n[MISSING FEATURES - What we SHOULD extract]")
print("  ✓ Rotation quaternion (rot_w, rot_x, rot_y, rot_z)")
print("  ✓ Pitch angle (up/down tilt) - HIGH vs LOW elevation")
print("  ✓ Roll angle (side tilt)")
print("  ✓ Yaw angle (rotation)")  
print("  ✓ Angular velocity (gyroscope equivalent from quaternion derivative)")
print("  ✓ Elevation proxy: acc_y range, acc_z forward lean")
print("  ✓ Thermal sensors (thm_1 through thm_5) - contact location")
print("  ✓ Time-of-Flight distance sensors (tof_1 through tof_5) - proximity")

# Calculate discrimination power
print("\n" + "=" * 80)
print("ELEVATION DISCRIMINATION ANALYSIS")
print("=" * 80)

high_data = train[train['gesture'].isin(high_elevation)]
low_data = train[train['gesture'].isin(low_elevation)]

print(f"\nHigh Elevation Gestures (n={len(high_data)}):")
print(f"  acc_y mean: {high_data['acc_y'].mean():7.3f}")
print(f"  acc_z mean: {high_data['acc_z'].mean():7.3f}")
print(f"  rot_x mean: {high_data['rot_x'].mean():7.3f}")

print(f"\nLow Elevation Gestures (n={len(low_data)}):")
print(f"  acc_y mean: {low_data['acc_y'].mean():7.3f}")
print(f"  acc_z mean: {low_data['acc_z'].mean():7.3f}")
print(f"  rot_x mean: {low_data['rot_x'].mean():7.3f}")

print(f"\nDifference (High - Low):")
print(f"  Δ acc_y: {high_data['acc_y'].mean() - low_data['acc_y'].mean():7.3f} ← Vertical position")
print(f"  Δ acc_z: {high_data['acc_z'].mean() - low_data['acc_z'].mean():7.3f} ← Forward lean")
print(f"  Δ rot_x: {high_data['rot_x'].mean() - low_data['rot_x'].mean():7.3f} ← Pitch angle")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("""
1. ADD ROTATION FEATURES (0 currently → should have 12+):
   - Quaternion to Euler angles (pitch, roll, yaw)
   - Angular velocity (derivative of quaternion)
   - Rotation magnitude and direction
   
2. ADD ELEVATION INDICATORS:
   - acc_y percentile (0-100% → high/mid/low)
   - rot_x pitch angle (up/down orientation)
   - acc_z forward lean (bending down = high acc_z)
   
3. ADD THERMAL FEATURES:
   - thm_1 through thm_5 mean/std/max
   - Thermal gradient (which sensors are hot = contact location)
   
4. ADD TIME-OF-FLIGHT FEATURES:
   - tof_1 through tof_5 distance readings (64 values each)
   - Proximity patterns (close = touching, far = reaching)
   
5. FEATURE ENGINEERING:
   - gesture_height_cluster = {HIGH, MID, LOW} based on acc_y
   - contact_pattern = thermal sensor activation sequence
   - reach_distance = ToF sensor readings
   
CURRENT: 12 features (only accelerometer mean/std/max/min)
PROPOSED: 80+ features (accel + rotation + thermal + ToF + derived)

This explains why:
  - "Forehead - scratch" (65.6%) ← HIGH ELEVATION, decent accuracy
  - "Above ear - pull hair" (56.2%) ← HIGH ELEVATION, moderate
  - "Scratch knee/leg skin" (18.8%) ← LOW ELEVATION, terrible!
  - "Pinch knee/leg skin" (62.5%) ← LOW ELEVATION, but pinch has thermal

We're MISSING the vertical dimension entirely!
""")

print("=" * 80)
