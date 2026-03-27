from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.vlm_extractor import extract_macro_features
from backend.drug_lookup import lookup_drug
from backend.synthesizer import synthesize_response
import base64

app = FastAPI(title="Medication ID Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze-image")
async def analyze_image(file: UploadFile):
    """Phase 2: Extract macro-features from pill image using VLM."""
    image_bytes = await file.read()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    features = await extract_macro_features(b64_image)
    return JSONResponse(content={
        "status": "awaiting_imprint",
        "extracted_features": features,
        "copilot_message": (
            f"I can see the pill appears to be **{features.get('color', 'unknown color')}** "
            f"and **{features.get('shape', 'unknown shape')}**. "
            "To identify it safely, could you please type the alphanumeric imprint "
            "stamped on the pill? (e.g., M365, L484)"
        )
    })


@app.post("/identify")
async def identify_pill(
    color: str = Form(...),
    shape: str = Form(...),
    imprint: str = Form(...)
):
    """Phases 3-5: Look up drug in NIH/FDA and synthesize patient-friendly response."""
    drug_data = await lookup_drug(color=color, shape=shape, imprint=imprint)

    if not drug_data:
        return JSONResponse(content={
            "status": "no_match",
            "copilot_message": (
                "I was unable to find a match in the NIH RxImage database for that "
                "color, shape, and imprint combination. Please double-check the imprint "
                "and consult a licensed pharmacist for a definitive identification."
            )
        })

    summary = await synthesize_response(drug_data)
    return JSONResponse(content={
        "status": "identified",
        "source": "NIH RxImage / OpenFDA",
        "raw_data": drug_data,
        "copilot_message": summary
    })
