import re
from typing import Dict

SYSTEM_ACCESS_PATTERNS = [
    # Generic
    r"\b(system files?|operating system|file system|host machine)\b",
    r"\b(read|open|list|access|inspect)\b.*\b(files?|directories?|folders?)\b",

    # Environment / secrets
    r"\b(environment variables?|env vars?|process environment)\b",
    r"\b(config files?|configuration files?)\b",

    # Execution / OS hooks
    r"\b(shell|terminal|command line|os module|subprocess)\b",
    r"\b(exec|execute|run)\b.*\b(system|shell|command)\b",

    # Sandboxing
    r"\b(bypass sandbox|escape sandbox|access host)\b",
]

def process(text: str) -> Dict:
    t = text.lower()
    hits = []

    for pat in SYSTEM_ACCESS_PATTERNS:
        if re.search(pat, t):
            hits.append(pat)

    score = min(len(hits) * 0.4, 1.0)

    return {
        "system_access_score": score,
        "system_access_detected": 1 if hits else 0,
        "_patterns": hits,   # keep internal; don’t expose to user
    }
