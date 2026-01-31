"""
Injection Phrase Detection Module

Detects explicit prompt injection attempts by matching
known override and role-manipulation phrases.

Outputs a numeric injection score and matched patterns
for explainable classification.
"""

from typing import Dict, List

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now system",
    "reveal system prompt",
    "bypass safeguards",
    "override rules",
    "forget your role",
]

def process(text: str, history: list | None = None) -> Dict:
    """
    Detect direct prompt-injection phrases.

    Returns:
    {
        "injection_score": float,  # 0.0–1.0
        "matched_patterns": List[str]
    }
    """
    t = (text or "").lower()
    matched: List[str] = []

    for pattern in INJECTION_PATTERNS:
        if pattern in t:
            matched.append(pattern)

    # Each strong phrase contributes 0.4, capped at 1.0
    score = min(len(matched) * 0.4, 1.0)

    return {
        "injection_score": score,
        "matched_patterns": matched
    }
