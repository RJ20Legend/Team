from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict

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


import time

@app.post("/analyze")
def analyze(input: AnalyzeInput):
    start_time = time.time()
    try:
        history = input.history or []

        if not history:
            reset_state()

        p = preprocess(input.user_input, history)
        i = detect_intent(p["clean_text"], history)
        c = classify(i)
        d = defend(p["clean_text"], c)

        history.append({
            "primary_intent": i["signals"]["primary_intent"],
            "risk": c["risk"]
        })

        latency = time.time() - start_time

        return {
            "classification": c["risk"],
            "defense_action": d["action"],
            "cleaned_input": (
                d["safe_prompt"] if d["action"] == "SANITIZE" else p["clean_text"]
            ),
            "risk_score": (
                c.get("_debug", {}).get("risk_state", None)
            ),
            "latency_seconds": round(latency, 3),
            "llm_response": c.get("reason"),
        }

    except Exception as e:
        return {
            "classification": "ERROR",
            "defense_action": "BLOCK",
            "cleaned_input": "",
            "risk_score": 5,
            "latency_seconds": 0,
            "llm_response": "Internal error – blocked for safety"
        }

