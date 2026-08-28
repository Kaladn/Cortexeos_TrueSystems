# ONE-SHOT BUILD ADDENDUM - FILE 14

## FILE 14: workers/predictor.py

### COPILOT INSTRUCTIONS:
**Create a worker that learns temporal offsets and predicts future pattern breaks.**

**PSEUDOCODE:**

```python
"""
Predictor Worker
Learns temporal offsets and predicts future pattern breaks based on upcoming events.
"""

from typing import List, Dict, Any
from datetime import timedelta

class Predictor:
    def __init__(self, config):
        """
        INITIALIZE:
        - config: Configuration dictionary
        - learned_offsets: Dictionary to store event_type -> avg_offset_days
        """
        self.learned_offsets = {}

    def learn_offsets(self, enriched_breaks: List[Dict[str, Any]]):
        """
        LEARN TEMPORAL OFFSETS FROM ENRICHED PATTERN BREAKS:

        INPUT:
            enriched_breaks: List of pattern breaks with causal_event from EventMapper

        OUTPUT:
            Dictionary of learned offsets (event_type -> avg_offset_days)

        ALGORITHM:
            offsets_by_type = {}
            FOR each p_break in enriched_breaks:
                IF p_break["causal_event"]:
                    event = p_break["causal_event"]
                    offset = p_break["timestamp"] - event["timestamp"]
                    event_type = event["category"]
                    
                    if event_type not in offsets_by_type:
                        offsets_by_type[event_type] = []
                    offsets_by_type[event_type].append(offset.days)

            FOR event_type, offsets in offsets_by_type.items():
                self.learned_offsets[event_type] = sum(offsets) / len(offsets)

            RETURN self.learned_offsets
        """
        # ... (Implementation)
        pass

    def predict(self, upcoming_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        PREDICT FUTURE PATTERN BREAKS:

        INPUT:
            upcoming_events: List of known future events (e.g., from a calendar)

        OUTPUT:
            List of predictions with event, predicted_date, and confidence.

        ALGORITHM:
            predictions = []
            FOR each event in upcoming_events:
                event_type = event["category"]
                if event_type in self.learned_offsets:
                    offset = self.learned_offsets[event_type]
                    predicted_date = event["timestamp"] + timedelta(days=offset)
                    
                    prediction = {
                        "event": event,
                        "predicted_date": predicted_date,
                        "confidence": 0.75 # Placeholder
                    }
                    predictions.append(prediction)

            RETURN predictions
        """
        # ... (Implementation)
        pass

    def backtest(self, historical_data: List[Dict[str, Any]], train_split=0.8):
        """
        BACKTEST THE PREDICTIVE MODEL:

        ALGORITHM:
            1. SPLIT historical_data into training and testing sets
            2. LEARN offsets from the training set
            3. MAKE predictions on the testing set
            4. COMPARE predictions to actual pattern breaks in the test set
            5. CALCULATE accuracy, precision, recall
            6. RETURN backtest results dictionary
        """
        # ... (Implementation)
        pass

```

**COPILOT: Implement the `learn_offsets` and `predict` functions. The `backtest` function can be a more advanced implementation for later.**
