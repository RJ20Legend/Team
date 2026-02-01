from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import time

from modules.system_access_detector import process as detect_system_access
from modules.preprocessor import process as preprocess
from modules.intent_detector import process as detect_intent
from modules.classifier import process as classify, reset_state
from modules.defense import process as defend

# 🚨 THIS MUST COME BEFORE ANY @app decorators
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
class AnalyzeInput(BaseModel):
    user_input: str
    history: Optional[List[Dict]] = None



@app.post("/analyze")
def analyze(input: AnalyzeInput):
    start_time = time.time()

    try:
        # 🔥 DEMO-SAFE: reset state per request
        reset_state()

        history = input.history or []

        # 1️⃣ Preprocess
        p = preprocess(input.user_input, history)
        clean_text = p["clean_text"]

        # 🚨 2️⃣ HARD SYSTEM ACCESS CHECK (NEW – CRITICAL)
        system_access = detect_system_access(clean_text)

        if system_access.get("system_access_detected"):
            latency = round(time.time() - start_time, 3)
            return {
                "classification": "MALICIOUS",
                "reason": "System-level file or command access detected",
                "defense_action": "BLOCK",
                "cleaned_input": "",
                "risk_score": 1.0,
                "latency_seconds": latency,
            }

        # 3️⃣ Intent detection (signals only)
        i = detect_intent(clean_text, history)

        # 4️⃣ Classification (ML + rule aggregation)
        c = classify(i, debug=True)

        # 5️⃣ Defense / enforcement
        d = defend(clean_text, c)

        latency = round(time.time() - start_time, 3)

        return {
            "classification": c["risk"],
            "reason": c.get("reason"),
            "defense_action": d["action"],
            "cleaned_input": d["safe_prompt"],
            "risk_score": c.get("_debug", {}).get("current_risk"),
            "latency_seconds": latency,
            "debug": c.get("_debug"),
        }

    except Exception as e:
        return {
            "classification": "ERROR",
            "defense_action": "BLOCK",
            "cleaned_input": "",
            "risk_score": 1.0,
            "latency_seconds": round(time.time() - start_time, 3),
            "reason": f"Internal error - blocked for safety: {str(e)}",
        }
