import os
import re
import glob
import random
import time
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, ConfusionMatrixDisplay
from sklearn.utils.multiclass import unique_labels

# === CONFIG ===
PACKAGE_DIR = "ml_packages"
LABEL_PATTERN = re.compile(r"pkg__(.*?)\.txt")
OUTPUT_MODEL = "trained_model.pkl"

# === FUNCTIONS ===

def plot_confusion_matrix_lite(y_true, y_pred, top_n=20):
    top_labels = [label for label, _ in Counter(y_true).most_common(top_n)]
    mask = [label in top_labels for label in y_true]
    filtered_y_true = [y for y, m in zip(y_true, mask) if m]
    filtered_y_pred = [y for y, m in zip(y_pred, mask) if m]
    
    ConfusionMatrixDisplay.from_predictions(
        filtered_y_true,
        filtered_y_pred,
        xticks_rotation=90,
        cmap='Blues'
    )
    plt.title(f"Confusion Matrix (Top {top_n} Classes)")
    plt.tight_layout()
    plt.show()

def load_training_data():
    texts = []
    labels = []

    files = glob.glob(os.path.join(PACKAGE_DIR, "pkg__*.txt"))
    if not files:
        raise FileNotFoundError("No ML packages found to train on.")

    for file in tqdm(files, desc="📂 Loading Files"):
        match = LABEL_PATTERN.search(os.path.basename(file))
        label = match.group(1) if match else "general"
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            chunks = content.split("\n\n---\n\n")
            texts.extend(chunks)
            labels.extend([label] * len(chunks))

    return texts, labels

def filter_and_group_classes(texts, labels, min_count=5):
    label_counts = Counter(labels)
    grouped_labels = []
    for label in labels:
        if label_counts[label] < min_count:
            grouped_labels.append("miscellaneous")
        else:
            grouped_labels.append(label)
    return texts, grouped_labels

# === MAIN PIPELINE ===
def train_model():
    start_time = time.time()
    print("📦 Loading and preparing training data...")
    texts, labels = load_training_data()
    print(f"🧾 Total Samples (before filtering): {len(texts)}")

    texts, labels = filter_and_group_classes(texts, labels)
    print(f"🧾 Total Samples (after filtering rare classes): {len(texts)}")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    print("🔠 Vectorizing with TF-IDF...")
    vectorizer = TfidfVectorizer(max_features=5000)
    X_train_vec = vectorizer.fit_transform(tqdm(X_train, desc="Vectorizing Train"))
    X_test_vec = vectorizer.transform(tqdm(X_test, desc="Vectorizing Test"))

    print("🧠 Training RandomForest classifier...")
    model = RandomForestClassifier(n_estimators=200, random_state=42, verbose=1)
    model.fit(X_train_vec, y_train)

    print("📊 Evaluation Results:")
    y_pred = model.predict(X_test_vec)
    report = classification_report(y_test, y_pred, output_dict=True)
    print(classification_report(y_test, y_pred))

    print("📈 Plotting performance metrics...")
    plot_confusion_matrix_lite(y_test, y_pred, top_n=20)

    categories = list(report.keys())[:-3]  # Skip avg/total entries
    f1_scores = [report[cat]['f1-score'] for cat in categories if isinstance(report[cat], dict)]
    plt.figure(figsize=(10, 6))
    plt.bar(categories, f1_scores, color='green')
    plt.ylabel("F1 Score")
    plt.title("F1 Score by Class")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

    print(f"⏱️ Total Training Time: {round(time.time() - start_time, 2)} seconds")
    print("✅ ML Model training complete. Ready for module integration.")

if __name__ == '__main__':
    train_model()
