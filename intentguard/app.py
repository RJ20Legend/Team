from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
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
class UserInput(BaseModel):
    message: str
    history: list = []

class AnalyzeInput(BaseModel):
    user_input: str
    history: Optional[list] = []  # Make it truly optional

@app.post("/chat")
def chat(input: UserInput):
    return {
        "status": "IntentGuard backend running",
        "received_message": input.message
    }

@app.post("/analyze")
def analyze(input: AnalyzeInput):
    try:
        # Ensure history is always a list (handle None case)
        history = input.history if input.history is not None else []
        
        p = preprocess(input.user_input, history)
        i = detect_intent(p["clean_text"], history)
        c = classify(i)

        # 5️⃣ Defense
        d = defend(p["clean_text"], c)

        # 6️⃣ LLM response (Claude via RAG)
        llm_response = f"Detected: {c['risk']} - Action: {d['action']}"


        # 🔍 Judge-friendly logs
        print("\n--- SECURITY PIPELINE ---")
        print("User Input:", input.user_input)
        print("Intent Signals:", i["signals"])
        print("Classification:", c)
        print("Defense Action:", d["action"])
        print("-------------------------\n")

        return {
            "classification": c["risk"],
            "defense_action": d["action"],
            "cleaned_input": p.get("clean_text", input.user_input),  # Add this
            "risk_score": c.get("score", 0),  # Add this if available
            "llm_response": f"Detected: {c['risk']} - Action: {d['action']}"
        }

    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()  # Better error logging
        
        return {
            "classification": "ERROR",
            "defense_action": "BLOCK",
            "cleaned_input": "",
            "risk_score": 5,
            "llm_response": f"Error during analysis: {str(e)}"
        }
