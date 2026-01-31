"""
Preprocessing Module

Responsibilities:
- Light text normalization
- Tokenization
- Extraction of simple, explainable security signals

NOTE:
- This module does NOT make security decisions.
- Output is consumed by intent_detector, classifier, and defense.
"""

import re
from typing import List, Dict

SUSPICIOUS_KEYWORDS = {
    "ignore", "override", "bypass", "assume", "authorized",
    "unrestricted", "disable", "reveal", "system", "rules",
    "instructions", "policy", "developer", "admin"
}


def clean_text(text: str) -> str:
    """
    Light normalization only.
    Do NOT aggressively sanitize — intent lives in wording.
    """
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> List[str]:
    """
    Simple word tokenizer.
    Keeps meaningful words for intent analysis.
    """
    return re.findall(r"\b\w+\b", text.lower())


def extract_signals(text: str, tokens: List[str], history: List[Dict]) -> Dict:
    """
    Extract lightweight, explainable preprocessing signals.
    """

    signals: Dict = {}

    # Length-based signals
    signals["char_length"] = len(text)
    signals["token_length"] = len(tokens)

    # ALL CAPS ratio (aggressive prompts)
    signals["caps_ratio"] = (
        sum(1 for c in text if c.isupper()) / len(text)
        if text else 0.0
    )

    # Keyword presence
    keyword_hits = SUSPICIOUS_KEYWORDS.intersection(tokens)
    signals["keyword_hits"] = list(keyword_hits)
    signals["keyword_count"] = len(keyword_hits)

    # Imperative phrasing
    signals["starts_with_verb"] = (
        tokens[0] in {"ignore", "reveal", "explain", "tell", "assume", "act"}
        if tokens else False
    )

    # Obfuscation hints (NOT detection)
    signals["contains_base64_like"] = bool(
        re.search(r"[A-Za-z0-9+/]{20,}={0,2}", text)
    )

    signals["contains_encoding_terms"] = any(
        t in tokens for t in {"encode", "decode", "translate", "base64", "rot13"}
    )

    # Conversation context
    signals["history_length"] = len(history)
    signals["has_prior_intent"] = len(history) > 0

    return signals


def process(text: str, history: List[Dict]) -> Dict:
    """
    Main preprocessing entry point.

    Returns:
    {
      "raw_text": original text,
      "clean_text": normalized + lowercased text (canonical),
      "tokens": token list,
      "signals": preprocessing signals
    }
    """

    clean = clean_text(text)
    tokens = tokenize(clean)
    signals = extract_signals(clean, tokens, history)

    return {
        "raw_text": text,
        "clean_text": clean.lower(),   # canonical text for ML & detectors
        "tokens": tokens,
        "signals": signals
    }
