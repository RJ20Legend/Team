from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel

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

class AnalyzeInput(BaseModel):
    user_input: str
    history: list = []

@app.post("/chat")
def chat():
    return {"status": "IntentGuard backend running"}

@app.post("/analyze")
def analyze(input: AnalyzeInput):
    try:
        # 0️⃣ Reset classifier state for new conversations
        if not input.history:
            reset_state()

        history = input.history or []

        # 1️⃣ Preprocess
        p = preprocess(input.user_input, history)

        # 2️⃣ Intent detection
        i = detect_intent(p["clean_text"], history)

        # 3️⃣ Update history (only what is needed)
        history.append({
            "primary_intent": i["signals"]["primary_intent"]
        })

        # 4️⃣ Classification
        c = classify(i)

        # 5️⃣ Defense
        d = defend(p["clean_text"], c)

        # 6️⃣ Simulated LLM response
        if d["action"] == "BLOCK":
            llm_response = d["safe_prompt"]
        else:
            llm_response = f"(Simulated LLM Response to): {d['safe_prompt']}"

        # 🔍 Console logs (judge-friendly)
        print("\n--- SECURITY PIPELINE ---")
        print("User Input:", input.user_input)
        print("Intent Signals:", i["signals"])
        print("Classification:", c)
        print("Defense Action:", d["action"])
        print("-------------------------\n")

        return {
            "classification": c["risk"],
            "defense_action": d["action"],
            "llm_response": llm_response,
            "updated_history": history
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "classification": "ERROR",
            "defense_action": "BLOCK",
            "llm_response": "Error handled safely"
        }
