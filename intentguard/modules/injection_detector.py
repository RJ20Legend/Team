# modules/injection_detector.py

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "you are now system",
    "you are the system",
    "reveal hidden policy",
    "reveal system prompt",
    "bypass safeguards",
    "bypass safety",
    "override rules",
    "forget your role",
    "act as system"
]

def process(text, history=None):
    """
    Detect direct prompt injection attempts.
    """
    t = text.lower()
    matched = [p for p in INJECTION_PATTERNS if p in t]

    injection_score = min(1.0, 0.2 * len(matched))

    return {
        "injection_score": injection_score,
        "matched_patterns": matched
    }
