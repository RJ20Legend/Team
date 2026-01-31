# module/intent_detector.py

PRIMARY_KEYWORDS = {
    "code_review": ["review", "audit", "vulnerability", "security"],
    "policy_check": ["policy", "compliance", "rule", "violate"]
}

META_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "bypass",
    "override",
    "system prompt",
    "forget your rules"
]

def detect_primary_intent(text):
    t = text.lower()
    for intent, keywords in PRIMARY_KEYWORDS.items():
        if any(k in t for k in keywords):
            return intent
    return "unknown"

def detect_meta_intent(text):
    t = text.lower()
    for p in META_PATTERNS:
        if p in t:
            return "override_attempt"
    return "none"

def compute_drift(history, current_intent):
    if not history:
        return 0.0
    initial_intent = history[0].get("primary_intent", current_intent)
    if initial_intent == current_intent:
        return 0.0
    if "unknown" in (initial_intent, current_intent):
        return 0.3
    return 0.7

def detect_intent(text, history):
    primary = detect_primary_intent(text)
    meta = detect_meta_intent(text)
    drift = compute_drift(history, primary)
    return {
        "output": text,
        "signals": {
            "primary_intent": primary,
            "meta_intent": meta,
            "intent_drift": drift
        }
    }
def process(text, history):
    return detect_intent(text, history)

