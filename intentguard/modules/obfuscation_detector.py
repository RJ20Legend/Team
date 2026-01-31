"""
Obfuscation Detection Module

Detects hidden or encoded prompt injection attempts using:
- Unicode normalization differences
- Base64-like encodings
- Spaced-out text patterns
- Excessive special character usage

Returns a numeric obfuscation score with human-readable reasons.
"""

import re
import unicodedata

BASE64_REGEX = re.compile(r"(?:[A-Za-z0-9+/]{20,}={0,2})")
SPACED_WORD_REGEX = re.compile(r"(?:\b\w\s){4,}\w")


def process(text, history=None):
    reasons = []
    score = 0.0

    normalized = unicodedata.normalize("NFKC", text)
    if normalized != text:
        reasons.append("Unicode normalization difference")
        score += 0.3

    if BASE64_REGEX.search(text):
        reasons.append("Base64-like encoded content")
        score += 0.4

    if SPACED_WORD_REGEX.search(text.lower()):
        reasons.append("Suspicious spaced-out text")
        score += 0.3

    special_ratio = sum(not c.isalnum() for c in text) / max(len(text), 1)
    if special_ratio > 0.3:
        reasons.append("High special character ratio")
        score += 0.2

    return {
        "obfuscation_score": min(score, 1.0),
        "reason": ", ".join(reasons) if reasons else "None"
    }
