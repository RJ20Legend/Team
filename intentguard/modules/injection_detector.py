"""
Injection Phrase Detection Module

Detects explicit and contextual prompt injection attempts:
- Direct override phrases
- Roleplay/persona hijacking
- Boundary/role marker spoofing
- Instruction hidden inside quoted or embedded data

Returns SAFE abstract signals by default.
Detailed matches are available only in debug mode.
"""

from typing import Dict, List
import re

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now system",
    "reveal system prompt",
    "bypass safeguards",
    "override rules",
    "forget your role",
]

ROLEPLAY_PATTERNS = [
    r"\bpretend (to be|you are)\b",
    r"\bact as\b",
    r"\brole[- ]?play as\b",
    r"\byou are now\b",
    r"\bin this (story|scenario|simulation)\b",
    r"\bsimulate being\b",
    r"\bwithout (any )?restrictions\b",
    r"\bno (rules|policies) apply\b",
]

BOUNDARY_SPOOF_PATTERNS = [
    r"\b(system|assistant|developer|user)\s*:",
    r"<\s*(system|assistant|developer|user)\s*>",
    r"#+\s*(system|assistant) prompt",
    r"\bend of (system|assistant) message\b"
]

IMPERATIVE_VERBS = [
    "ignore", "follow", "execute", "reveal",
    "print", "show", "list", "describe", "disclose"
]


def detect_roleplay(text: str) -> List[str]:
    return [p for p in ROLEPLAY_PATTERNS if re.search(p, text, re.IGNORECASE)]


def detect_boundary_spoof(text: str) -> List[str]:
    return [p for p in BOUNDARY_SPOOF_PATTERNS if re.search(p, text, re.IGNORECASE)]


def detect_instruction_in_data(text: str) -> List[str]:
    has_embedded = bool(re.search(r'["\']{1}.*?["\']{1}', text, re.DOTALL)) or "```" in text
    verbs = [v for v in IMPERATIVE_VERBS if re.search(rf"\b{v}\b", text, re.IGNORECASE)]
    return verbs if has_embedded and verbs else []


def process(text: str, history: list | None = None, debug: bool = False) -> Dict:
    t = (text or "").lower()

    matched = [p for p in INJECTION_PATTERNS if p in t]
    roleplay_hits = detect_roleplay(t)
    boundary_hits = detect_boundary_spoof(t)
    data_hits = detect_instruction_in_data(t)

    score = 0.0
    score += min(len(matched) * 0.4, 0.8)
    score += 0.5 if roleplay_hits else 0.0
    score += 0.6 if boundary_hits else 0.0
    score += 0.6 if data_hits else 0.0

    # ✅ SAFE OUTPUT
    result = {
        "injection_score": min(score, 1.0),
        "roleplay_detected": 1 if roleplay_hits else 0,
        "boundary_spoof_detected": 1 if boundary_hits else 0,
        "instruction_in_data": 1 if data_hits else 0,
    }

    # 🔒 INTERNAL DEBUG ONLY
    if debug:
        result.update({
            "_matched_patterns": matched,
            "_roleplay_patterns": roleplay_hits,
            "_boundary_spoof_patterns": boundary_hits,
            "_instruction_in_data_verbs": data_hits,
        })

    return result
