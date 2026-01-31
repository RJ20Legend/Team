# ml/train_intent_model.py

import json
import re
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


# ----------------------------
# Utilities
# ----------------------------
def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def clean_text(text: str) -> str:
    """
    Light cleaning (same philosophy as fake news detector).
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


# ----------------------------
# Load datasets
# ----------------------------
benign = load_jsonl("../data/benign_prompts_500.jsonl")
suspicious = load_jsonl("../data/suspicious_prompts_600.jsonl")
malicious = load_jsonl("../data/malicious_prompts_500.jsonl")

df = pd.DataFrame(benign + suspicious + malicious)

label_map = {
    "benign": 0,
    "suspicious": 1,
    "malicious": 2
}

df["label_id"] = df["label"].map(label_map)
df["clean_text"] = df["prompt"].apply(clean_text)

X = df["clean_text"]
y = df["label_id"]

print("\nDataset distribution:")
print(df["label"].value_counts())


# ----------------------------
# Vectorization
# ----------------------------
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=6000,
    min_df=3
)

X_vec = vectorizer.fit_transform(X)


# ----------------------------
# Train / test split
# ----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X_vec,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)


# ----------------------------
# Model
# ----------------------------
model = LogisticRegression(
    max_iter=1000,
    class_weight="balanced"
)

model.fit(X_train, y_train)


# ----------------------------
# Evaluation
# ----------------------------
y_pred = model.predict(X_test)

print("\n=== Classification Report ===")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=label_map.keys()
    )
)


# ----------------------------
# Save artifacts
# ----------------------------
joblib.dump(model, "intentguard_model.pkl")
joblib.dump(vectorizer, "intentguard_vectorizer.pkl")

print("\n✅ Model and vectorizer saved successfully")
