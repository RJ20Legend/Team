from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional

from llm.generate import generate_answer
from llm.rag import retrieve, index, texts
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
    history: Optional[List[Dict]] = None


@app.get("/health")
def health():
    return {"status": "IntentGuard backend running"}


@app.post("/analyze")
def analyze(input: AnalyzeInput):
    try:
        # Reset classifier state ONLY for new conversations
        if not input.history:
            reset_state()

        history = input.history or []

        # 1️⃣ Preprocess
        p = preprocess(input.user_input, history)

        # 2️⃣ Intent detection
        i = detect_intent(p["clean_text"], history)

        # 3️⃣ Update history (minimal, explainable)
        history.append({
            "primary_intent": i["signals"]["primary_intent"]
        })

        # 4️⃣ Classification
        c = classify(i)

        # 5️⃣ Defense
        d = defend(p["clean_text"], c)

        # 6️⃣ LLM response (Claude via RAG)
        if d["action"] == "BLOCK":
            llm_response = d["safe_prompt"]
        else:
            docs = retrieve(d["safe_prompt"], index, texts)
            context = "\n".join(docs)

            llm_response = generate_answer(
                prompt=d["safe_prompt"],
                context=context
            )

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
            "defense_note": d.get("note"),
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
