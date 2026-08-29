"""
CortexOS Evaluation Wrapper

- Bridges Kaggle evaluation API with lawful cognition output.
- Fully I/O compliant with Kaggle requirements.
"""

import pandas as pd

class EvaluationWrapper:
    def __init__(self, classifier_model, test_sequence_ids):
        self.classifier = classifier_model
        self.test_sequence_ids = test_sequence_ids

    def run_inference(self):
        """Run full inference on test set."""
        gesture_results = self.classifier.classify_specific_gesture()
        
        predictions = {}
        for sequence_id in self.test_sequence_ids:
            if sequence_id in gesture_results:
                predictions[sequence_id] = gesture_results[sequence_id]
            else:
                predictions[sequence_id] = "unknown"  # Fallback for unmatched sequences
        return predictions

    def generate_submission(self, output_path="submission/kaggle_submission.csv"):
        """Produce Kaggle-compliant submission file."""
        predictions = self.run_inference()
        submission_df = pd.DataFrame.from_dict(predictions, orient='index').reset_index()
        submission_df.columns = ['sequence_id', 'gesture']
        submission_df.to_csv(output_path, index=False)
        print(f"✅ Lawful Kaggle submission file written to {output_path}")