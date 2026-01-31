# modules/classifier.py

from __future__ import annotations
from typing import Dict, Any

# --- Tunable thresholds ---
SAFE_MAX = 0.30
SUSPICIOUS_MAX = 0.60

# meta label(s) coming from your intent detector
STRONG_META = {"override_attempt"}  # you currently output only this

# Single internal state (hackathon demo). For multi-user, make this per session_id.
_STATE = {
    "risk_state": 0.0,          # running aggregated risk (0..1)
    "override_hits": 0,         # number of strong meta hits seen
    "suspicious_streak": 0,     # consecutive turns with drift >= SAFE_MAX
    "turns": 0
}

# how much to remember history (0.8 = strong memory, 0.6 = forget faster)
DECAY = 0.80


def _clamp01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, x))


def process(intent_packet: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    """
    Expects the exact output of detect_intent(text, history) from your intent_detector.py

    intent_packet = {
      "output": "...",
      "signals": {
        "primary_intent": "...",
        "meta_intent": "...",
        "intent_drift": 0.7
      }
    }

    Returns ONLY decision:
    { "risk": "SAFE|SUSPICIOUS|MALICIOUS", "reason": "..." }
    """

    signals = intent_packet.get("signals", {}) or {}

    primary = (signals.get("primary_intent", "unknown") or "unknown").strip().lower()
    meta = (signals.get("meta_intent", "none") or "none").strip().lower()
    drift = _clamp01(signals.get("intent_drift", 0.0))

    # --- Detect high-confidence instant-block phrases (LLM security) ---
    text = (intent_packet.get("output", "") or "").lower()
    INSTANT_BLOCK_PHRASES = [
        "system prompt",
        "developer message",
        "hidden key",
        "api key",
        "secret",
        "sensitive data",
        "exfiltrate",
        "leak",
    ]
    instant_block = any(p in text for p in INSTANT_BLOCK_PHRASES)

    # --- 1) per-turn risk from drift + meta ---
    current_risk = drift

    # Count override attempts
    if meta in STRONG_META:
        # graded boost: override is bad; override + drift is worse
        current_risk = max(current_risk, 0.75 + 0.25 * drift)
        _STATE["override_hits"] += 1

    # If instant-block phrase exists, force malicious-level risk
    # Also count it as an override hit even if meta is "none" (for consistency)
    if instant_block:
        current_risk = 1.0
        if meta not in STRONG_META:
            _STATE["override_hits"] += 1

    # streak tracking (used for escalation)
    if drift >= SAFE_MAX:
        _STATE["suspicious_streak"] += 1
    else:
        _STATE["suspicious_streak"] = 0

    # --- 2) compress history into risk_state ---
    _STATE["risk_state"] = _clamp01(DECAY * _STATE["risk_state"] + (1 - DECAY) * current_risk)
    _STATE["turns"] += 1

    rs = _STATE["risk_state"]
    streak = _STATE["suspicious_streak"]
    overrides = _STATE["override_hits"]

    # --- 3) classification rules (LLM-safety friendly) ---

    # Instant block decision AFTER state update (so debug/counters are correct)
    if instant_block:
        out = {"risk": "MALICIOUS", "reason": "High-confidence secret/exfiltration request"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # Repeated override attempts => malicious
    if overrides >= 2:
        out = {"risk": "MALICIOUS", "reason": "Repeated override attempts across turns"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # First override attempt => suspicious, unless also strong drift
    if overrides == 1:
        if drift >= 0.6:
            out = {"risk": "MALICIOUS", "reason": "Override attempt + high drift"}
        else:
            out = {"risk": "SUSPICIOUS", "reason": "Override attempt detected (first occurrence)"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # Sustained high risk => malicious
    if rs > SUSPICIOUS_MAX:
        out = {"risk": "MALICIOUS", "reason": "Sustained high risk across conversation (aggregated)"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # High drift without override => suspicious (task switching)
    if meta == "none" and drift >= 0.6:
        out = {"risk": "SUSPICIOUS", "reason": "High intent drift (task change) without override intent"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # aggregated moderate risk or streak => suspicious
    if rs >= SAFE_MAX or streak >= 3:
        out = {"risk": "SUSPICIOUS", "reason": "Moderate risk or repeated drift (aggregated escalation)"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    out = {"risk": "SAFE", "reason": "Intent stable (low drift and low aggregated risk)"}
    return _attach_debug(out, debug, primary, meta, drift, current_risk)


def reset_state():
    """Call this at start of a new chat/session (or when pipeline resets)."""
    _STATE["risk_state"] = 0.0
    _STATE["override_hits"] = 0
    _STATE["suspicious_streak"] = 0
    _STATE["turns"] = 0


def _attach_debug(out: Dict[str, Any], debug: bool, primary: str, meta: str, drift: float, current_risk: float):
    if debug:
        out["_debug"] = {
            "primary_intent": primary,
            "meta_intent": meta,
            "intent_drift": drift,
            "current_risk": current_risk,
            "risk_state": _STATE["risk_state"],
            "override_hits": _STATE["override_hits"],
            "suspicious_streak": _STATE["suspicious_streak"],
            "turns": _STATE["turns"],
            "decay": DECAY,
        }
    return out