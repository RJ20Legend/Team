"""
Injection Phrase Detection Module

Detects explicit prompt injection attempts by matching
known override and role-manipulation phrases.

Outputs a numeric injection score and matched patterns
for explainable classification.
"""

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now system",
    "reveal system prompt",
    "bypass safeguards",
    "override rules",
    "forget your role"
]


def process(text, history=None):
    t = text.lower()
    matched = []

    for p in INJECTION_PATTERNS:
        if p in t:
            matched.append(p)

    score = min(len(matched) * 0.4, 1.0)

    return {
        "injection_score": score,
        "matched_patterns": matched
    }
