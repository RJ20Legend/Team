from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel

from modules.preprocessor import process as preprocess
from modules.intent_detector import process as detect_intent
from modules.classifier import process as classify
from modules.defense import process as defend

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserInput(BaseModel):
    message: str
    history: list = []

class AnalyzeInput(BaseModel):
    user_input: str
    history: list = []

@app.post("/chat")
def chat(input: UserInput):
    return {
        "status": "IntentGuard backend running",
        "received_message": input.message
    }

@app.post("/analyze")
def analyze(input: AnalyzeInput):
    try:
        p = preprocess(input.user_input, input.history)
        i = detect_intent(p["clean_text"], input.history)
        c = classify(i)
        d = defend(p["clean_text"], c)

        print("INPUT:", input.user_input)
        print("RISK:", c["risk"])
        print("ACTION:", d["action"])

        return {
            "classification": c["risk"],
            "defense_action": d["action"],
            "llm_response": "Security review response here"
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "classification": "ERROR",
            "defense_action": "BLOCK",
            "llm_response": "Error handled safely"
        }

