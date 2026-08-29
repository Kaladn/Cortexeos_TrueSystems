import os
import re
import glob
import random
import time
import joblib
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, ConfusionMatrixDisplay

# === CONFIG ===
PACKAGE_DIR = "ml_packages"
INPUT_DROP_DIR = "input_drop"
LABEL_PATTERN = re.compile(r"pkg__(.*?)\.txt")
OUTPUT_MODEL = "trained_model.pkl"
OUTPUT_VECTORIZER = "vectorizer.pkl"
RARE_CLASS_THRESHOLD = 2
MAX_CLASSES_IN_PLOT = 20

# === TEXT ANALYTICS ===
def extract_word_contexts(text, window=1):
    tokens = text.split()
    context_pairs = []
    for i in range(len(tokens)):
        word = tokens[i]
        before = tokens[i - window] if i - window >= 0 else None
        after = tokens[i + window] if i + window < len(tokens) else None
        context_pairs.append((word, before, after))
    return context_pairs

def save_context_stats(contexts, output_dir="context_stats"):
    abs_path = os.path.abspath(output_dir)
    os.makedirs(abs_path, exist_ok=True)
    print(f"📝 Writing context stats to: {abs_path}")
    word_freq = Counter()
    before_context = defaultdict(Counter)
    after_context = defaultdict(Counter)

    for word, before, after in contexts:
        word_freq[word] += 1
        if before: before_context[word][before] += 1
        if after: after_context[word][after] += 1

    with open(os.path.join(output_dir, "word_freq.txt"), 'w', encoding='utf-8') as f:
        for word, freq in word_freq.most_common():
            f.write(f"{word}: {freq}\n")

    with open(os.path.join(output_dir, "before_context.txt"), 'w', encoding='utf-8') as f:
        for word, context in before_context.items():
            f.write(f"{word}: {dict(context)}\n")

    with open(os.path.join(output_dir, "after_context.txt"), 'w', encoding='utf-8') as f:
        for word, context in after_context.items():
            f.write(f"{word}: {dict(context)}\n")

# === INGESTION FROM DROP ===
def process_input_drop():
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    files = glob.glob(os.path.join(INPUT_DROP_DIR, "*.txt"))
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        label = os.path.splitext(os.path.basename(file))[0]
        package_path = os.path.join(PACKAGE_DIR, f"pkg__{label}.txt")
        with open(package_path, 'w', encoding='utf-8') as out:
            out.write(content)
        print(f"✅ Imported {file} as {package_path}")

# === LOAD DATA ===
def load_training_data():
    texts = []
    labels = []
    all_contexts = []

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
            for chunk in chunks:
                all_contexts.extend(extract_word_contexts(chunk))

    save_context_stats(all_contexts)
    return texts, labels

# === FILTER RARE CLASSES ===
def filter_rare_classes(texts, labels, min_count=RARE_CLASS_THRESHOLD):
    label_counts = Counter(labels)
    filtered_texts = []
    filtered_labels = []

    for text, label in zip(texts, labels):
        if label_counts[label] >= min_count:
            filtered_texts.append(text)
            filtered_labels.append(label)
        else:
            filtered_texts.append(text)
            filtered_labels.append("miscellaneous")

    return filtered_texts, filtered_labels

# === PREDICT INTERFACE ===
def predict_sample(sample_text):
    if not os.path.exists(OUTPUT_MODEL) or not os.path.exists(OUTPUT_VECTORIZER):
        raise RuntimeError("Model or vectorizer not found. Please train the model first.")

    model = joblib.load(OUTPUT_MODEL)
    vectorizer = joblib.load(OUTPUT_VECTORIZER)
    vec = vectorizer.transform([sample_text])
    prediction = model.predict(vec)[0]
    return prediction

# === MAIN PIPELINE ===
def train_model():
    process_input_drop()
    start_time = time.time()
    print("📦 Loading and preparing training data...")
    texts, labels = load_training_data()
    print(f"🧾 Total Samples (before filtering): {len(texts)}")

    texts, labels = filter_rare_classes(texts, labels)
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

    # Save model and vectorizer
    joblib.dump(model, OUTPUT_MODEL)
    joblib.dump(vectorizer, OUTPUT_VECTORIZER)
    print(f"💾 Model saved to: {OUTPUT_MODEL}")
    print(f"💾 Vectorizer saved to: {OUTPUT_VECTORIZER}")

    print("📊 Evaluation Results:")
    y_pred = model.predict(X_test_vec)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    print(classification_report(y_test, y_pred, zero_division=0))

    print("📈 Plotting performance metrics...")
    common_labels = Counter(y_test).most_common(MAX_CLASSES_IN_PLOT)
    top_classes = [label for label, _ in common_labels]
    y_test_top = [y if y in top_classes else "other" for y in y_test]
    y_pred_top = [y if y in top_classes else "other" for y in y_pred]

    ConfusionMatrixDisplay.from_predictions(
        y_test_top, y_pred_top, xticks_rotation=45, cmap='Blues'
    )
    plt.title("Confusion Matrix (Top Classes)")
    plt.tight_layout()
    plt.show()

    categories = list(report.keys())[:-3]
    top_report = [cat for cat in categories if cat in top_classes]
    f1_scores = [report[cat]['f1-score'] for cat in top_report if isinstance(report[cat], dict)]

    plt.figure(figsize=(10, 6))
    plt.bar(top_report, f1_scores, color='green')
    plt.ylabel("F1 Score")
    plt.title("Top Class F1 Scores")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

    print(f"⏱️ Total Training Time: {round(time.time() - start_time, 2)} seconds")
    print("✅ ML Model training complete. Ready for module integration.")

if __name__ == '__main__':
    train_model()