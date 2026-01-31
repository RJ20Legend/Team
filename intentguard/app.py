from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
import time

from modules.preprocessor import process as preprocess
from modules.intent_detector import process as detect_intent
from modules.classifier import process as classify, reset_state
from modules.defense import process as defend

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Schemas ----------------

class UserInput(BaseModel):
    message: str
    history: Optional[List[Dict]] = None


class AnalyzeInput(BaseModel):
    user_input: str
    history: Optional[List[Dict]] = None


# ---------------- Routes ----------------

@app.post("/chat")
def chat(input: UserInput):
    return {
        "status": "IntentGuard backend running",
        "received_message": input.message
    }


@app.post("/analyze")
def analyze(input: AnalyzeInput):
    start_time = time.time()

    try:
        # 🔥 DEMO-SAFE: always reset state to avoid cross-request escalation
        reset_state()

        history = input.history or []

        # 1️⃣ Preprocess
        p = preprocess(input.user_input, history)

        # 2️⃣ Intent detection (signals only)
        i = detect_intent(p["clean_text"], history)

        # 3️⃣ Classification (ML + rules)
        c = classify(i, debug=True)

        # 4️⃣ Defense / enforcement
        d = defend(p["clean_text"], c)

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
            "reason": f"Internal error – blocked for safety: {str(e)}",
        }
