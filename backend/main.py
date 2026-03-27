from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.pill_classifier import classify_pill
from backend.sdtm_logger import log_exposure, log_questionnaire
import json
import base64
from pathlib import Path

app = FastAPI(title="Clinical Trial Medication Compliance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROTOCOL = json.loads(Path("config/protocol.json").read_text())
QUESTIONS = json.loads(Path("data/smaq_questions.json").read_text())


@app.get("/questionnaire")
def get_questionnaire():
    """Returns the full questionnaire for the current trial visit."""
    return {
        "trial_id": PROTOCOL["trial_id"],
        "visit": PROTOCOL["visit"],
        "questions": QUESTIONS["questions"]
    }


@app.post("/questionnaire/submit")
async def submit_questionnaire(responses: dict):
    """Logs questionnaire responses to SDTM QS domain."""
    subject_id = PROTOCOL["subject_id"]
    for qid, answer in responses.items():
        log_questionnaire(
            study_id=PROTOCOL["trial_id"],
            subject_id=subject_id,
            qstest=qid,
            qsorres=answer
        )
    return {"status": "logged", "next_step": "pill_verification"}


@app.post("/verify-pill")
async def verify_pill(file: UploadFile):
    """
    Phase 2: Classify the submitted pill image using the custom CNN.
    Returns match status against the protocol expected pill.
    Blocks progression if wrong pill detected.
    """
    image_bytes = await file.read()
    expected_ids = [p["id"] for p in PROTOCOL["expected_pills"]]
    expected_names = {p["id"]: p["name"] for p in PROTOCOL["expected_pills"]}

    result = classify_pill(image_bytes, expected_ids)
    predicted_id = result["predicted_id"]
    confidence = result["confidence"]

    if predicted_id in expected_ids and confidence >= 0.85:
        return JSONResponse(content={
            "status": "match",
            "predicted_id": predicted_id,
            "predicted_name": expected_names[predicted_id],
            "confidence": confidence,
            "message": f"✅ Correct medication identified: {expected_names[predicted_id]}. Please take your medication and confirm below."
        })
    else:
        return JSONResponse(status_code=400, content={
            "status": "no_match",
            "predicted_id": predicted_id,
            "confidence": confidence,
            "message": "❌ Incorrect medication detected. Please ensure you are holding the correct pill and try again. Do not proceed until the correct medication is verified."
        })


@app.post("/confirm-ingestion")
async def confirm_ingestion(pill_id: str = Form(...)):
    """
    Phase 3: Patient confirms they have taken the medication.
    Logs to SDTM EX domain.
    """
    pill_info = next((p for p in PROTOCOL["expected_pills"] if p["id"] == pill_id), None)
    if not pill_info:
        return JSONResponse(status_code=404, content={"error": "Unknown pill_id"})

    log_exposure(
        study_id=PROTOCOL["trial_id"],
        subject_id=PROTOCOL["subject_id"],
        treatment=pill_info["name"],
        ndc=pill_info["ndc"]
    )

    return {
        "status": "confirmed",
        "message": "Ingestion recorded. Proceeding to next question.",
        "next_step": "next_question"
    }
