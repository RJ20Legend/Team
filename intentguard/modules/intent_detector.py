# modules/intent_detector.py

from modules.obfuscation_detector import process as detect_obfuscation

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


def detect_primary_intent(text: str) -> str:
    t = text.lower()
    for intent, keywords in PRIMARY_KEYWORDS.items():
        if any(k in t for k in keywords):
            return intent
    return "unknown"


def detect_meta_intent(text: str) -> str:
    t = text.lower()
    for p in META_PATTERNS:
        if p in t:
            return "override_attempt"
    return "none"


def compute_drift(history, current_intent: str) -> float:
    if not history:
        return 0.0

    previous_intents = [
        h.get("primary_intent")
        for h in history
        if isinstance(h, dict) and "primary_intent" in h
    ]

    if not previous_intents:
        return 0.0

    last_intent = previous_intents[-1]

    if last_intent == current_intent:
        return 0.0

    if "unknown" in (last_intent, current_intent):
        return 0.3

    return 0.7


def detect_intent(text, history, debug=False):
    primary = detect_primary_intent(text)
    meta = detect_meta_intent(text)
    drift = compute_drift(history, primary)

    # Obfuscation detection
    obf = detect_obfuscation(text, history)

    result = {
        "output": text,
        "signals": {
            "primary_intent": primary,
            "meta_intent": meta,
            "intent_drift": drift,
            "obfuscation_score": obf["obfuscation_score"],
            "obfuscation_reason": obf["reason"]
        }
    }

    if debug:
        print("Intent Signals:", result["signals"])

    return result


# === Interface freeze wrapper ===
def process(text, history):
    return detect_intent(text, history)
