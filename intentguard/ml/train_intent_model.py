# ml/train_intent_model.py

import json
import re
import os
import joblib
import pandas as pd

from sklearn.pipeline import FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


# ======================================================
# Path setup (ROBUST – works from anywhere)
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")


# ======================================================
# Utilities
# ======================================================
def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def clean_text(text: str) -> str:
    """
    Light cleaning.
    DO NOT remove symbols – scripts & system commands need them.
    """
    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ======================================================
# Load BASE datasets (JSONL)
# ======================================================
benign = load_jsonl(os.path.join(DATA_DIR, "benign_9000.jsonl"))
suspicious = load_jsonl(os.path.join(DATA_DIR, "merged_suspicious_dataset.jsonl"))
malicious = load_jsonl(os.path.join(DATA_DIR, "merged_8500.jsonl"))

base_df = pd.DataFrame(benign + suspicious + malicious)

TEXT_COL = "text" if "text" in base_df.columns else "prompt"
base_df = base_df[[TEXT_COL, "label"]].rename(columns={TEXT_COL: "text"})


# ======================================================
# Load SYSTEM ACCESS / PROMPT INJECTION dataset (PARQUET)
# ======================================================
system_df = pd.read_parquet(
    os.path.join(DATA_DIR, "0000_train.parquet")
)

# Map numeric labels → IntentGuard labels
# 0 = benign, 1 = attack / injection
system_df["label"] = system_df["label"].map({
    0: "benign",
    1: "malicious"
})

# Drop unexpected labels
system_df = system_df.dropna(subset=["label"])

# Keep required columns only
system_df = system_df[["text", "label"]]


# ======================================================
# Merge ALL datasets
# ======================================================
df = pd.concat(
    [base_df, system_df],
    ignore_index=True
)


# ======================================================
# Label encoding
# ======================================================
label_map = {
    "benign": 0,
    "suspicious": 1,
    "malicious": 2
}

df["label_id"] = df["label"].map(label_map)
df = df.dropna(subset=["label_id"])


# ======================================================
# Text cleaning
# ======================================================
df["clean_text"] = df["text"].apply(clean_text)

X = df["clean_text"]
y = df["label_id"]

print("\n================ DATASET DISTRIBUTION ================")
print(df["label"].value_counts())
print("======================================================\n")


# ======================================================
# Vectorization (WORD + CHAR)
# ======================================================
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
            ngram_range=(4, 5),
            max_features=5000
        )
    )
])

X_vec = vectorizer.fit_transform(X)


# ======================================================
# Train / test split
# ======================================================
X_train, X_test, y_train, y_test = train_test_split(
    X_vec,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)


# ======================================================
# Model
# ======================================================
model = LogisticRegression(
    max_iter=1200,
    class_weight="balanced",
    n_jobs=-1
)

model.fit(X_train, y_train)


# ======================================================
# Evaluation
# ======================================================
y_pred = model.predict(X_test)

print("\n================ CLASSIFICATION REPORT ================")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=["benign", "suspicious", "malicious"]
    )
)
print("======================================================\n")


# ======================================================
# Save artifacts
# ======================================================
joblib.dump(model, "intentguard_model.pkl")
joblib.dump(vectorizer, "intentguard_vectorizer.pkl")

print("\n✅ Model and vectorizer saved successfully")
