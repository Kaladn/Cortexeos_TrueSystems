"""Debug test for new detectors."""
import json
import numpy as np
from cod_616.arc_organ.arc_task_runner import ArcGridPair
from cod_616.arc_organ.arc_recognition_field_v2 import ARCRecognitionFieldV2

# Load a416b8f3 (should match HorizontalReplicateDetector)
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    train_data = json.load(f)

task_id = 'a416b8f3'
task = train_data[task_id]

train_examples = [
    ArcGridPair(np.array(ex['input']), np.array(ex['output']))
    for ex in task['train']
]

print(f"Testing {task_id}")
print(f"Example 1: {train_examples[0].input_grid.shape} → {train_examples[0].output_grid.shape}")

# Test recognition
recognizer = ARCRecognitionFieldV2()

class MockSig:
    pass

hypotheses = recognizer.recognize_task(train_examples, MockSig())

print(f"\n{'='*60}")
print(f"DETECTED RULES:")
print(f"{'='*60}")

if hypotheses:
    for i, hyp in enumerate(hypotheses, 1):
        print(f"\n{i}. {hyp.family.name}")
        print(f"   Confidence: {hyp.confidence:.2f}")
        print(f"   Reasoning: {hyp.reasoning}")
        print(f"   Params: {hyp.params}")
else:
    print("No rules detected!")
