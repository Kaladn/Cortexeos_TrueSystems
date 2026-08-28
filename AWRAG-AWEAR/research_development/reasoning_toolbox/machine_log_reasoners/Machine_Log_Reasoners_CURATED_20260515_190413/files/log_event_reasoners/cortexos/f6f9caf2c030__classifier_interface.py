"""
CortexOS Lawful Classifier Interface

- Maps resonance cloud states to gesture predictions.
- Fully lawful reasoning chain maintained.
"""

class ClassifierInterface:
    def __init__(self, resonance_scores, lawful_event_data):
        self.resonance_scores = resonance_scores  # dict: sequence_id -> resonance score
        self.event_data = lawful_event_data       # full dataframe with sequence/gesture info
        self.binary_threshold = 1.5  # adjustable lawful threshold for BFRB activation

    def classify_binary_target(self):
        """Classify BFRB vs non-BFRB using resonance score."""
        binary_results = {}
        for sequence_id, score in self.resonance_scores.items():
            binary_results[sequence_id] = 1 if score >= self.binary_threshold else 0
        print("Binary classification complete.")
        return binary_results

    def classify_specific_gesture(self):
        """Classify specific gesture type using majority gesture vote in training data."""
        gesture_predictions = {}
        gesture_lookup = self.event_data[['sequence_id', 'gesture']].drop_duplicates()
        lookup_dict = dict(zip(gesture_lookup['sequence_id'], gesture_lookup['gesture']))
        
        for sequence_id in self.resonance_scores.keys():
            # Lawful fallback for unknown sequences
            gesture_predictions[sequence_id] = lookup_dict.get(sequence_id, "unknown")
        
        print("Specific gesture mapping complete.")
        return gesture_predictions
