# modules/classifier.py

from __future__ import annotations
from typing import Dict, Any

from ml.intent_predictor import predict_intent
from modules.injection_detector import detect as detect_injection
from modules.obfuscation_detector import detect as detect_obfuscation

# --- Tunable thresholds ---
ML_MALICIOUS_HARD  = 0.75     # ML malicious at this conf → MALICIOUS
ML_MALICIOUS_SOFT  = 0.40     # ML malicious at this conf → SUSPICIOUS (closes the gap)
ML_SUSPICIOUS_CONF = 0.60     # ML suspicious at this conf → SUSPICIOUS
OBFUSCATION_BLOCK  = 0.60     # Obfuscation score to combine with ML malicious → MALICIOUS
SUSPICIOUS_STATE   = 0.60     # risk_state threshold for state-based escalation

STRONG_META = {"override_attempt"}

_STATE = {
    "risk_state": 0.0,
    "override_hits": 0,
    "suspicious_streak": 0,
    "turns": 0
}

DECAY = 0.80


def _clamp01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, x))


def process(intent_packet: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    """
    Hybrid classifier:
    - Injection detector (hard override)
    - ML intent classifier (tiered thresholds)
    - Obfuscation escalation
    - Stateful drift aggregation
    """

    signals = intent_packet.get("signals", {}) or {}
    text = (intent_packet.get("output", "") or "").lower()

    primary = (signals.get("primary_intent", "unknown") or "unknown").strip().lower()
    meta    = (signals.get("meta_intent", "none") or "none").strip().lower()
    drift   = _clamp01(signals.get("intent_drift", 0.0))

    # ==========================================================
    # 1️⃣ HARD OVERRIDE — Injection detector
    # ==========================================================
    injection = detect_injection(text)
    if injection["score"] >= 0.9:
        _STATE["override_hits"] += 1
        out = {
            "risk": "MALICIOUS",
            "reason": "Prompt injection detected",
            "evidence": injection["patterns"]
        }
        return _attach_debug(out, debug, primary, meta, drift, 1.0)

    # ==========================================================
    # 2️⃣ ML intent prediction
    # ==========================================================
    try:
        ml = predict_intent(text)
        ml_label = ml.get("label", "benign")
        ml_conf  = _clamp01(ml.get("confidence", 0.0))
        if ml_label not in ("benign", "suspicious", "malicious"):
            ml_label = "benign"
            ml_conf  = 0.0
    except Exception:
        ml_label = "benign"
        ml_conf  = 0.0

    # ==========================================================
    # 3️⃣ Obfuscation detection
    # ==========================================================
    obf = detect_obfuscation(text)
    obf_score = _clamp01(obf.get("score", 0.0))

    # ==========================================================
    # 4️⃣ Compute per-turn risk
    # ==========================================================
    current_risk = drift

    if meta in STRONG_META:
        current_risk = max(current_risk, 0.75 + 0.25 * drift)
        _STATE["override_hits"] += 1

    if ml_label == "malicious":
        current_risk = max(current_risk, ml_conf)

    if ml_label == "suspicious" and ml_conf >= ML_SUSPICIOUS_CONF:
        current_risk = max(current_risk, 0.5 * ml_conf)

    # ==========================================================
    # 5️⃣ Stateful aggregation
    # ==========================================================
    if drift >= 0.30:
        _STATE["suspicious_streak"] += 1
    else:
        _STATE["suspicious_streak"] = 0

    _STATE["risk_state"] = _clamp01(
        DECAY * _STATE["risk_state"] + (1 - DECAY) * current_risk
    )
    _STATE["turns"] += 1

    rs       = _STATE["risk_state"]
    streak   = _STATE["suspicious_streak"]
    overrides = _STATE["override_hits"]

    # ==========================================================
    # 6️⃣ FINAL DECISION — ordered from hardest to softest
    # ==========================================================

    # --- MALICIOUS gates ---

    # ML malicious + obfuscation (any confidence)
    if ml_label == "malicious" and obf_score >= OBFUSCATION_BLOCK:
        out = {"risk": "MALICIOUS", "reason": "ML malicious + obfuscation detected"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # Repeated override attempts across turns
    if overrides >= 2:
        out = {"risk": "MALICIOUS", "reason": "Repeated override attempts"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # High-confidence ML malicious
    if ml_label == "malicious" and ml_conf >= ML_MALICIOUS_HARD:
        out = {"risk": "MALICIOUS", "reason": "High-confidence ML malicious"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # --- SUSPICIOUS gates ---

    # Mid-confidence ML malicious → escalate to SUSPICIOUS (closes the gap)
    if ml_label == "malicious" and ml_conf >= ML_MALICIOUS_SOFT:
        out = {"risk": "SUSPICIOUS", "reason": "Mid-confidence ML malicious"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # ML suspicious with enough confidence
    if ml_label == "suspicious" and ml_conf >= ML_SUSPICIOUS_CONF:
        out = {"risk": "SUSPICIOUS", "reason": "ML suspicious"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # State or streak escalation
    if rs >= SUSPICIOUS_STATE or streak >= 3:
        out = {"risk": "SUSPICIOUS", "reason": "Stateful risk escalation"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # --- SAFE ---
    out = {"risk": "SAFE", "reason": "Low risk after hybrid analysis"}
    return _attach_debug(out, debug, primary, meta, drift, current_risk)


def reset_state():
    _STATE["risk_state"] = 0.0
    _STATE["override_hits"] = 0
    _STATE["suspicious_streak"] = 0
    _STATE["turns"] = 0


def _attach_debug(
    out: Dict[str, Any],
    debug: bool,
    primary: str,
    meta: str,
    drift: float,
    current_risk: float
):
    if debug:
        out["_debug"] = {
            "primary_intent": primary,
            "meta_intent": meta,
            "intent_drift": drift,
            "current_risk": round(current_risk, 3),
            "risk_state": round(_STATE["risk_state"], 3),
            "override_hits": _STATE["override_hits"],
            "suspicious_streak": _STATE["suspicious_streak"],
            "turns": _STATE["turns"],
            "decay": DECAY,
        }
    return out
