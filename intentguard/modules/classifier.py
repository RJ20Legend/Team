# modules/classifier.py

from __future__ import annotations
from typing import Dict, Any

from ml.intent_predictor import predict_intent
from modules.injection_detector import detect as detect_injection
from modules.obfuscation_detector import detect as detect_obfuscation

# --- Tunable thresholds ---
SAFE_MAX = 0.30
SUSPICIOUS_MAX = 0.60
ML_HIGH_CONF = 0.75          # ML confidence to trust malicious prediction
OBFUSCATION_BLOCK = 0.60     # Obfuscation score threshold

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
    - ML intent classifier
    - Obfuscation escalation
    - Stateful drift aggregation
    """

    signals = intent_packet.get("signals", {}) or {}
    text = (intent_packet.get("output", "") or "").lower()

    primary = (signals.get("primary_intent", "unknown") or "unknown").strip().lower()
    meta = (signals.get("meta_intent", "none") or "none").strip().lower()
    drift = _clamp01(signals.get("intent_drift", 0.0))

    # ==========================================================
    # 1️⃣ HARD OVERRIDE — Injection detector
    # ==========================================================
    injection = detect_injection(text)
    if injection["detected"]:
        _STATE["override_hits"] += 1
        out = {
            "risk": "MALICIOUS",
            "reason": "Prompt injection detected",
            "evidence": injection["patterns"]
        }
        return _attach_debug(out, debug, primary, meta, drift, 1.0)

    # ==========================================================
    # 2️⃣ ML intent prediction (advisory but strong)
    # ==========================================================
    ml = predict_intent(text)
    ml_label = ml["label"]
    ml_conf = ml["confidence"]

    # ==========================================================
    # 3️⃣ Obfuscation detection
    # ==========================================================
    obf = detect_obfuscation(text)
    obf_score = obf.get("score", 0.0)

    # ==========================================================
    # 4️⃣ Compute per-turn risk
    # ==========================================================
    current_risk = drift

    if meta in STRONG_META:
        current_risk = max(current_risk, 0.75 + 0.25 * drift)
        _STATE["override_hits"] += 1

    if ml_label == "malicious" and ml_conf >= ML_HIGH_CONF:
        current_risk = max(current_risk, ml_conf)

    if ml_label == "suspicious":
        current_risk = max(current_risk, 0.5 * ml_conf)

    # ==========================================================
    # 5️⃣ Stateful aggregation
    # ==========================================================
    if drift >= SAFE_MAX:
        _STATE["suspicious_streak"] += 1
    else:
        _STATE["suspicious_streak"] = 0

    _STATE["risk_state"] = _clamp01(
        DECAY * _STATE["risk_state"] + (1 - DECAY) * current_risk
    )
    _STATE["turns"] += 1

    rs = _STATE["risk_state"]
    streak = _STATE["suspicious_streak"]
    overrides = _STATE["override_hits"]

    # ==========================================================
    # 6️⃣ FINAL DECISION LOGIC
    # ==========================================================

    # ML + obfuscation => hard block
    if ml_label == "malicious" and obf_score >= OBFUSCATION_BLOCK:
        out = {"risk": "MALICIOUS", "reason": "ML malicious + obfuscation"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # Repeated overrides
    if overrides >= 2:
        out = {"risk": "MALICIOUS", "reason": "Repeated override attempts"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # Strong ML malicious
    if ml_label == "malicious" and ml_conf >= ML_HIGH_CONF:
        out = {"risk": "MALICIOUS", "reason": "High-confidence ML malicious"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

    # Suspicious ML or drift escalation
    if ml_label == "suspicious" or rs >= SAFE_MAX or streak >= 3:
        out = {"risk": "SUSPICIOUS", "reason": "ML or drift-based suspicion"}
        return _attach_debug(out, debug, primary, meta, drift, current_risk)

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
            "current_risk": current_risk,
            "risk_state": _STATE["risk_state"],
            "override_hits": _STATE["override_hits"],
            "suspicious_streak": _STATE["suspicious_streak"],
            "turns": _STATE["turns"],
            "decay": DECAY,
        }
    return out
