# ml/train_intent_model.py

import json
import re
import joblib
import pandas as pd

from sklearn.pipeline import FeatureUnion
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
    Light cleaning.
    DO NOT remove symbols aggressively — scripts need them.
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ----------------------------
# Load datasets
# ----------------------------
benign = load_jsonl("../data/benign_9000.jsonl")
suspicious = load_jsonl("../data/merged_suspicious_dataset.jsonl")
malicious = load_jsonl("../data/merged_8500.jsonl")

df = pd.DataFrame(benign + suspicious + malicious)

# ✅ Column safety (VERY IMPORTANT)
TEXT_COL = "text" if "text" in df.columns else "prompt"

label_map = {
    "benign": 0,
    "suspicious": 1,
    "malicious": 2
}

df["label_id"] = df["label"].map(label_map)
df["clean_text"] = df[TEXT_COL].astype(str).apply(clean_text)

X = df["clean_text"]
y = df["label_id"]

print("\nDataset distribution:")
print(df["label"].value_counts())


# ----------------------------
# Vectorization (WORD + CHAR)
# ----------------------------
vectorizer = FeatureUnion([
    (
        "word",
        TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=6000,
            min_df=2,
            lowercase=True
        )
    ),
    (
        "char",
        TfidfVectorizer(
            analyzer="char",
            ngram_range=(3, 5),
            max_features=8000
        )
    )
])

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
    max_iter=1500,
    class_weight="balanced",
    n_jobs=-1
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
        target_names=["benign", "suspicious", "malicious"]
    )
)


# ----------------------------
# Save artifacts
# ----------------------------
joblib.dump(model, "intentguard_model.pkl")
joblib.dump(vectorizer, "intentguard_vectorizer.pkl")

print("\n✅ Model and vectorizer saved successfully")
