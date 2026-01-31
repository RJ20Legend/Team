"""
Intent Detection Module

Extracts structured security signals from user prompts:
- Primary Intent
- Meta Intent (override attempts)
- Intent Drift (multi-turn goal change)
- Obfuscation Score
- Translation-Then-Execute Attacks
- Data Exfiltration Attempts
"""

from typing import Dict, Any, List
import re
from modules.obfuscation_detector import process as detect_obfuscation

PRIMARY_KEYWORDS = {
    "code_review": ["review", "audit", "vulnerability", "security"],
    "policy_check": ["policy", "compliance", "rule", "violate"],
}

META_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "bypass",
    "override",
    "system prompt",
    "forget your rules",
]

TRANSLATION_WORDS = ["translate", "convert to english", "decode this"]
ACTION_WORDS = ["follow", "execute", "obey", "apply", "do what it says"]

EXFIL_PATTERNS = [
    r"\bsystem prompt\b",
    r"\bhidden instructions\b",
    r"\breveal (your|the) (rules|instructions|policies)\b",
    r"\bwhat was said before\b",
    r"\bshow (your|the) full prompt\b",
    r"\bprint your (config|rules)\b"
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


def compute_drift(history: List[Dict[str, Any]], current_intent: str) -> float:
    if not history:
        return 0.0

    last_intent = history[-1].get("primary_intent")
    if last_intent == current_intent:
        return 0.0
    if "unknown" in (last_intent, current_intent):
        return 0.3
    return 0.7


def detect_translation_attack(text: str) -> float:
    t = text.lower()
    return 0.8 if any(w in t for w in TRANSLATION_WORDS) and any(
        w in t for w in ACTION_WORDS
    ) else 0.0


def detect_exfiltration(text: str) -> float:
    return 0.9 if any(re.search(p, text, re.IGNORECASE) for p in EXFIL_PATTERNS) else 0.0


def process(text: str, history: List[Dict[str, Any]], debug: bool = False) -> Dict[str, Any]:
    clean_text = (text or "").strip()

    primary = detect_primary_intent(clean_text)
    meta = detect_meta_intent(clean_text)
    drift = compute_drift(history, primary)

    obf = detect_obfuscation(clean_text, history)

    result = {
        "output": clean_text,
        "signals": {
            "primary_intent": primary,
            "meta_intent": meta,
            "intent_drift": drift,
            "obfuscation_score": obf["obfuscation_score"],
            "translation_attack_score": detect_translation_attack(clean_text),
            "exfiltration_score": detect_exfiltration(clean_text),
        },
    }

    return result
