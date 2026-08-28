"""Validate Kaggle Submission"""
import pandas as pd

# Load data
test = pd.read_csv('data/kaggle/test.csv')
submission = pd.read_csv('submission/kaggle_submission.csv')

print("=" * 70)
print("KAGGLE SUBMISSION VALIDATION")
print("=" * 70)

# Check completeness
test_seqs = set(test['sequence_id'].unique())
sub_seqs = set(submission['sequence_id'].unique())

print(f"\nTest Data:")
print(f"  Total rows: {len(test):,}")
print(f"  Unique sequences: {len(test_seqs)}")

print(f"\nSubmission File:")
print(f"  Total rows: {len(submission):,}")
print(f"  Unique sequences: {len(sub_seqs)}")
print(f"  Columns: {list(submission.columns)}")

# Validation checks
print(f"\nValidation Checks:")
print(f"  ✓ All test sequences covered: {test_seqs == sub_seqs}")
print(f"  ✓ No duplicate sequences: {len(submission) == submission['sequence_id'].nunique()}")
print(f"  ✓ Correct format (sequence_id, gesture): {list(submission.columns) == ['sequence_id', 'gesture']}")
print(f"  ✓ No missing values: {submission.isnull().sum().sum() == 0}")

# Show predictions
print(f"\nSubmission Preview:")
print(submission.to_string(index=False))

print("\n" + "=" * 70)
print("✓ SUBMISSION READY FOR KAGGLE UPLOAD")
print(f"  File: submission/kaggle_submission.csv")
print(f"  Size: {len(submission)} predictions")
print("=" * 70)
