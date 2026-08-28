from sklearn.ensemble import RandomForestClassifier

class GPUPredictiveMaintenance:
    def __init__(self):
        self.model = RandomForestClassifier()

    def train(self, historical_data, outcomes):
        """
        Train the model on historical GPU metrics.
        """
        self.model.fit(historical_data, outcomes)

    def predict_failure(self, current_metrics):
        """
        Predict GPU failure probability.
        """
        return self.model.predict_proba([current_metrics])[0][1]  # Probability of failure
