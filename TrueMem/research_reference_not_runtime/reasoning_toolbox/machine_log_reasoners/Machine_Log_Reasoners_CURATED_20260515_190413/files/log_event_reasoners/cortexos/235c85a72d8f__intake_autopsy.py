"""
CortexOS Intake Autopsy Module

- Responsible for parsing and verifying the raw Helios dataset structure.
- Ensures lawful data alignment prior to lawful event extraction.
"""

import pandas as pd
import os

class IntakeAutopsy:
    def __init__(self, data_path):
        self.data_path = data_path
        self.train = None
        self.train_demo = None
        self.test = None
        self.test_demo = None

    def load_data(self):
        """Load train, test, and demographics CSVs."""
        self.train = pd.read_csv(os.path.join(self.data_path, "train.csv"))
        self.train_demo = pd.read_csv(os.path.join(self.data_path, "train_demographics.csv"))
        self.test = pd.read_csv(os.path.join(self.data_path, "test.csv"))
        self.test_demo = pd.read_csv(os.path.join(self.data_path, "test_demographics.csv"))
        print("Datasets loaded successfully.")

    def validate_fields(self):
        """Ensure dataset columns match expected schema."""
        expected_train_fields = [
            'sequence_id', 'sequence_type', 'sequence_counter', 'subject',
            'gesture', 'orientation', 'behavior',
            'acc_x', 'acc_y', 'acc_z', 'rot_w', 'rot_x', 'rot_y', 'rot_z'
        ]
        
        # Validate base columns
        for field in expected_train_fields:
            if field not in self.train.columns:
                print(f"WARNING: Missing expected field in train data: {field}")

        # Validate demographics columns
        expected_demo_fields = [
            'subject', 'adult_child', 'age', 'sex', 'handedness',
            'height_cm', 'shoulder_to_wrist_cm', 'elbow_to_wrist_cm'
        ]
        for field in expected_demo_fields:
            if field not in self.train_demo.columns:
                print(f"WARNING: Missing expected field in train demographics: {field}")

        print("Schema validation completed.")

    def summarize_structure(self):
        """Output lawful schema summary for audit."""
        print("Train sequences:", self.train['sequence_id'].nunique())
        print("Test sequences:", self.test['sequence_id'].nunique())
        print("Subjects in train:", self.train_demo['subject'].nunique())
        print("Subjects in test:", self.test_demo['subject'].nunique())
