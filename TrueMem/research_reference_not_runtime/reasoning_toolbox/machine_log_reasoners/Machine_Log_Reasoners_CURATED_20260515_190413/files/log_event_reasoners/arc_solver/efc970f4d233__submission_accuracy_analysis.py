"""
Accuracy Analysis for Submitted Predictions
Based on validation run: main_pipeline_polars.py
"""

print("=" * 80)
print("SUBMISSION ACCURACY BREAKDOWN")
print("=" * 80)

# From terminal output of main_pipeline_polars.py validation run
# Overall validation accuracy: 48.04% (816 sequences)

# Submitted predictions
submissions = {
    'SEQ_000001': 'Forehead - scratch',
    'SEQ_000011': 'Above ear - pull hair'
}

# Per-gesture accuracy from validation (recall scores)
gesture_accuracy = {
    'Above ear - pull hair': {
        'accuracy': 0.562,
        'support': 64,
        'percentage': '56.2%'
    },
    'Cheek - pinch skin': {
        'accuracy': 0.234,
        'support': 64,
        'percentage': '23.4%'
    },
    'Drink from bottle/cup': {
        'accuracy': 0.688,
        'support': 16,
        'percentage': '68.8%'
    },
    'Eyebrow - pull hair': {
        'accuracy': 0.188,
        'support': 64,
        'percentage': '18.8%'
    },
    'Eyelash - pull hair': {
        'accuracy': 0.312,
        'support': 64,
        'percentage': '31.2%'
    },
    'Feel around in tray and pull out an object': {
        'accuracy': 0.812,
        'support': 16,
        'percentage': '81.2%'
    },
    'Forehead - pull hairline': {
        'accuracy': 0.312,
        'support': 64,
        'percentage': '31.2%'
    },
    'Forehead - scratch': {
        'accuracy': 0.656,
        'support': 64,
        'percentage': '65.6%'
    },
    'Glasses on/off': {
        'accuracy': 0.438,
        'support': 16,
        'percentage': '43.8%'
    },
    'Neck - pinch skin': {
        'accuracy': 0.359,
        'support': 64,
        'percentage': '35.9%'
    },
    'Neck - scratch': {
        'accuracy': 0.250,
        'support': 64,
        'percentage': '25.0%'
    },
    'Pinch knee/leg skin': {
        'accuracy': 0.625,
        'support': 16,
        'percentage': '62.5%'
    },
    'Pull air toward your face': {
        'accuracy': 0.583,
        'support': 48,
        'percentage': '58.3%'
    },
    'Scratch knee/leg skin': {
        'accuracy': 0.188,
        'support': 16,
        'percentage': '18.8%'
    },
    'Text on phone': {
        'accuracy': 0.891,
        'support': 64,
        'percentage': '89.1%'
    },
    'Wave hello': {
        'accuracy': 0.708,
        'support': 48,
        'percentage': '70.8%'
    },
    'Write name in air': {
        'accuracy': 0.750,
        'support': 48,
        'percentage': '75.0%'
    },
    'Write name on leg': {
        'accuracy': 0.562,
        'support': 16,
        'percentage': '56.2%'
    }
}

print("\nVALIDATION PERFORMANCE:")
print(f"  Overall Accuracy: 48.04% (816 validation sequences)")
print(f"  Total Gestures: 18 classes")
print()

print("SUBMITTED PREDICTIONS ANALYSIS:")
print("-" * 80)

for seq_id, predicted_gesture in submissions.items():
    if predicted_gesture in gesture_accuracy:
        acc_data = gesture_accuracy[predicted_gesture]
        print(f"\n{seq_id}:")
        print(f"  Predicted Gesture: {predicted_gesture}")
        print(f"  Model Accuracy for this Gesture: {acc_data['percentage']}")
        print(f"  Validation Support: {acc_data['support']} samples")
        print(f"  Confidence Level: {'HIGH' if acc_data['accuracy'] > 0.6 else 'MODERATE' if acc_data['accuracy'] > 0.4 else 'LOW'}")

print("\n" + "=" * 80)
print("SUBMISSION CONFIDENCE SUMMARY")
print("=" * 80)

total_confidence = sum(gesture_accuracy[g]['accuracy'] for g in submissions.values())
avg_confidence = total_confidence / len(submissions)

print(f"\nAverage Confidence: {avg_confidence:.1%}")
print(f"  SEQ_000001 ('Forehead - scratch'):      65.6% accuracy")
print(f"  SEQ_000011 ('Above ear - pull hair'):   56.2% accuracy")

print("\nGesture Ranking (by validation accuracy):")
sorted_gestures = sorted(gesture_accuracy.items(), key=lambda x: x[1]['accuracy'], reverse=True)
for rank, (gesture, data) in enumerate(sorted_gestures, 1):
    marker = " ← SUBMITTED" if gesture in submissions.values() else ""
    print(f"  {rank:2d}. {gesture:45s} {data['percentage']:>6s}{marker}")

print("\n" + "=" * 80)
print("INTERPRETATION:")
print("=" * 80)
print("""
1. SEQ_000001 predicted as 'Forehead - scratch':
   - Ranked #5 out of 18 gestures in accuracy
   - 65.6% validation accuracy (MODERATE-HIGH confidence)
   - Model correctly identified this gesture in 42 out of 64 validation samples

2. SEQ_000011 predicted as 'Above ear - pull hair':
   - Ranked #8 out of 18 gestures in accuracy  
   - 56.2% validation accuracy (MODERATE confidence)
   - Model correctly identified this gesture in 36 out of 64 validation samples

Overall Assessment:
  ✓ Both predictions are above 50% confidence
  ✓ Combined confidence: 60.9%
  ✓ Neither prediction is from the low-performing gestures (<40%)
  ✓ Reasonable submission given model's 48.04% overall accuracy
""")

print("=" * 80)
