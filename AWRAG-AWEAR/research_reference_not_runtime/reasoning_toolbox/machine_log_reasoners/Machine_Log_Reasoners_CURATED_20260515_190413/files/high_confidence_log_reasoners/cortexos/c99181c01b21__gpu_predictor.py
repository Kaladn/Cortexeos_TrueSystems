from sklearn.ensemble import RandomForestClassifier

class GPUPredictor:
    def __init__(self):
        self.model = RandomForestClassifier()

    def train(self, X, y):
        """
        Train the model with GPU metrics (X) and outcomes (y).
        """
        self.model.fit(X, y)

    def predict(self, metrics):
        """
        Predict the likelihood of a GPU failure based on metrics.
        """
        return self.model.predict(metrics)
