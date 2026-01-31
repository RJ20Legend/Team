"""
Obfuscation Detection Module

Detects hidden or encoded prompt injection attempts using:
- Unicode normalization differences
- Base64-like encodings
- Spaced-out text patterns
- Excessive special character usage
"""

import re
import unicodedata
from typing import Dict, List, Optional

BASE64_REGEX = re.compile(r"(?:[A-Za-z0-9+/]{20,}={0,2})")
SPACED_WORD_REGEX = re.compile(r"(?:\b\w\s){4,}\w")

def process(text: Optional[str], history=None) -> Dict[str, str]:
    reasons: List[str] = []
    score = 0.0

    clean_text = (text or "").strip()

    # Unicode normalization trick
    normalized = unicodedata.normalize("NFKC", clean_text)
    if normalized != clean_text:
        reasons.append("Unicode normalization difference")
        score += 0.3

    # Base64-like payload
    if BASE64_REGEX.search(clean_text):
        reasons.append("Base64-like encoded content")
        score += 0.4

    # Spaced-out words (e.g., s y s t e m)
    if SPACED_WORD_REGEX.search(clean_text.lower()):
        reasons.append("Suspicious spaced-out text")
        score += 0.3

    # Excessive special characters
    special_ratio = sum(not c.isalnum() for c in clean_text) / max(len(clean_text), 1)
    if special_ratio > 0.3:
        reasons.append("High special character ratio")
        score += 0.2

    return {
        "obfuscation_score": min(score, 1.0),
        "reason": ", ".join(reasons) if reasons else "None",
    }
