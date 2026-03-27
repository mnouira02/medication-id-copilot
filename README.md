# 💊 Clinical Trial Medication Compliance Verifier

> **A gated ePRO system for clinical trials** — patients complete an adherence questionnaire, verify the correct pill via webcam using a custom-trained CNN, confirm ingestion, and only then advance to the next question. All events are logged in SDTM-compliant format.

---

## Executive Summary

Medication non-compliance is one of the leading causes of failed clinical trials. This system enforces **verified medication compliance** at the point of care using a multi-step gated workflow: structured questionnaire → webcam pill verification → ingestion confirmation → SDTM audit log.

The pill verification layer uses a **custom-trained CNN** (ResNet18 fine-tuned on the NIH C3PI dataset) loaded with the trial's expected medication list from a protocol config file. If the wrong pill is presented, the system **blocks progression** entirely — no skipping, no guessing.

---

## Compliance Workflow

```
┌─────────────────────────────────────────────────────┐
│  STEP 1: Questionnaire                              │
│  Patient answers adherence questions (SMAQ-based)   │
│  e.g. "Did you miss any doses this week?"           │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  STEP 2: Pill Verification (Webcam + CNN)           │
│  ROI overlay centers pill → 224×224px crop          │
│  CNN classifies against protocol expected_pill_id   │
│  ✅ Match → proceed   ❌ No match → BLOCKED         │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  STEP 3: Ingestion Confirmation                     │
│  Patient confirms: "I have taken the medication"    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  STEP 4: SDTM Logging                               │
│  EX domain: exposure event logged with timestamp    │
│  QS domain: questionnaire responses logged          │
└─────────────────────────────────────────────────────┘
                     │
              Next Question ──► Repeat from STEP 1
```

---

## System Architecture

| Layer | Component | Role |
|-------|-----------|------|
| Frontend | HTML5 + Vanilla JS | Gated multi-step UI with progress bar |
| Edge | HTML5 Canvas API | Real-time video crop (224×224 ROI) |
| Backend | Python FastAPI | Orchestration, session state, SDTM logging |
| AI | Custom CNN (ResNet18) | Pill classification against protocol list |
| Training Data | NIH C3PI Dataset | 133k consumer pill images |
| Protocol Config | `config/protocol.json` | Expected pills per trial visit |
| Audit | SDTM EX + QS domains | Regulatory-grade compliance logging |

---

## AI Architecture — Custom CNN

This project deliberately **does not use a general-purpose LLM or external API** for pill identification. Instead, it trains a closed-world classifier scoped to the exact medications in the trial protocol.

**Why a custom CNN over an LLM?**
- The model only needs to distinguish between N pills defined in `protocol.json` (typically 2–5)
- Closed-world classification is far more reliable than open-ended VLM guessing
- No API key, no latency, no hallucination risk
- The model can be re-trained per trial with zero code changes

**Architecture**: ResNet18 pretrained on ImageNet, final FC layer replaced with `N` output classes matching the protocol pill list. Fine-tuned on NIH C3PI consumer-grade images filtered to trial medications.

---

## Project Structure

```
medication-id-copilot/
├── frontend/
│   ├── index.html          # Gated multi-step UI: questions → webcam → confirm
│   ├── app.js              # Step state machine, Canvas ROI, CNN API calls
│   └── style.css           # Mobile-first dark UI with progress bar
├── backend/
│   ├── main.py             # FastAPI: /questionnaire /verify-pill /confirm /log-sdtm
│   ├── pill_classifier.py  # CNN inference: loads model.pt, returns pill_id + confidence
│   └── sdtm_logger.py      # SDTM EX + QS domain JSON log writer
├── model/
│   ├── cnn_pill_classifier.py  # ResNet18 model definition
│   └── train_cnn.py            # Training script — NIH C3PI dataset
├── config/
│   └── protocol.json       # Trial protocol: expected pills per visit
├── data/
│   └── smaq_questions.json # Validated SMAQ adherence questionnaire
├── docs/
│   ├── architecture.md     # System design decision log
│   └── sdtm_logging.md     # SDTM EX/QS domain spec
├── .env.example
└── requirements.txt
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- PyTorch 2.x (`pip install torch torchvision`)
- NIH C3PI Dataset (free, public domain)

### 1. Download Training Data
```bash
# NIH C3PI — 133k consumer-grade pill images (public domain)
wget https://data.lhncbc.nlm.nih.gov/public/Pills/trainingImages.zip
unzip trainingImages.zip -d data/raw/
```

### 2. Configure Your Trial Protocol
Edit `config/protocol.json` with your trial's expected medications:
```json
{
  "trial_id": "TRIAL-001",
  "visit": "Week 4",
  "expected_pills": [
    {"id": "pill_001", "name": "Atorvastatin 20mg", "ndc": "00071-0155"},
    {"id": "placebo",  "name": "Placebo",           "ndc": "00000-0000"}
  ]
}
```

### 3. Train the CNN
```bash
python model/train_cnn.py \
  --data data/raw/ \
  --protocol config/protocol.json \
  --epochs 50 \
  --output model/model.pt
```

### 4. Run the System
```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
# Open frontend/index.html in browser
```

---

## SDTM Output

Each session writes two SDTM-compliant JSON files:

**EX (Exposure) domain** — records verified medication ingestion:
```json
{"STUDYID": "TRIAL-001", "DOMAIN": "EX", "USUBJID": "SUBJ-042",
 "EXTRT": "Atorvastatin 20mg", "EXDOSE": 20, "EXDOSU": "mg",
 "EXSTDTC": "2026-03-27T11:32:00Z", "EXSTAT": "VERIFIED_BY_CNN"}
```

**QS (Questionnaire) domain** — records adherence responses:
```json
{"STUDYID": "TRIAL-001", "DOMAIN": "QS", "USUBJID": "SUBJ-042",
 "QSTEST": "SMAQ1", "QSORRES": "No", "QSDTC": "2026-03-27T11:31:00Z"}
```

---

## Safety & Regulatory Notes

> ⚠️ This is a **portfolio / research project** demonstrating clinical AI architecture patterns. It is not a certified medical device or validated eCOA system. For regulated clinical trials, output must be reviewed by qualified personnel and integrated with a validated EDC system (e.g. Medidata Rave).

---

## License

MIT — see [LICENSE](LICENSE)
