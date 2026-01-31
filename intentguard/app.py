import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# -------------------- IMPORT PIPELINE MODULES --------------------
from modules.preprocessor import process as preprocess
from modules.intent_detector import process as detect_intent
from modules.classifier import process as classify, reset_state
from modules.defense import process as defend
from modules.main_llm import generate_response
from modules.llm_reviewer import review_response
from modules.output_filter import verify_llm_output
# ----------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- REQUEST MODEL --------------------
class AnalyzeInput(BaseModel):
    user_input: str
    history: Optional[List[Dict]] = None
# ------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "IntentGuard backend running"}

@app.post("/analyze")
def analyze(input: AnalyzeInput):
    try:
        # 🧠 Reset classifier for new conversation
        if not input.history:
            reset_state()

        history = input.history or []

        # 1️⃣ PREPROCESS
        p = preprocess(input.user_input, history)

        # 2️⃣ INTENT DETECTION
        i = detect_intent(p["clean_text"], history)

        # 3️⃣ UPDATE HISTORY
        history.append({
            "primary_intent": i["signals"]["primary_intent"]
        })

        # 4️⃣ CLASSIFICATION
        c = classify(i)

        # 5️⃣ INPUT DEFENSE (FIREWALL)
        d = defend(p["clean_text"], c)

        # 🚫 BLOCK AT INPUT STAGE
        if d["action"] == "BLOCK":
            return {
                "classification": c["risk"],
                "defense_action": "BLOCK",
                "llm_response": d["safe_prompt"]
            }

        # 🤖 6️⃣ MAIN LLM RESPONSE
        llm_raw_response = generate_response(d["safe_prompt"])

        # 🛡 7️⃣ SECOND LLM SECURITY REVIEW
        review = review_response(llm_raw_response)

        # 🔒 GOLDEN RULE: ONLY BLOCK IF VERDICT == "UNSAFE"
        if review["verdict"] == "UNSAFE":
            return {
                "classification": "BLOCKED_BY_REVIEWER_LLM",
                "defense_action": "BLOCK",
                "llm_response": "⚠️ Response blocked by AI Security Reviewer.",
                "review_reason": review["reason"]
            }

        # 🧱 8️⃣ RULE‑BASED OUTPUT FILTER (FINAL BACKUP)
        output_check = verify_llm_output(llm_raw_response)

        if output_check["action"] == "BLOCK":
            return {
                "classification": "BLOCKED_BY_OUTPUT_FILTER",
                "defense_action": "BLOCK",
                "llm_response": output_check["safe_output"]
            }

        # ✅ 9️⃣ SAFE RESPONSE
        return {
            "classification": c["risk"],
            "defense_action": "ALLOW",
            "llm_response": llm_raw_response,
            "review_verdict": review["verdict"],
            "updated_history": history
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "classification": "ERROR",
            "defense_action": "BLOCK",
            "llm_response": "System error handled safely."
        }

# Debug confirmation (safe to keep)
print("API KEY LOADED:", OPENROUTER_API_KEY[:10] if OPENROUTER_API_KEY else "NOT FOUND")
