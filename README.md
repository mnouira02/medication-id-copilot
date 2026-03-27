# 💊 Medication ID Copilot

> **A Safe-Fail Multimodal Healthcare AI** — Portfolio project demonstrating responsible AI architecture for consumer health applications.

![Architecture](docs/architecture.png)

---

## Executive Summary

The **Medication ID Copilot** is a lightweight, edge-compatible web application designed to identify general prescription medications safely. Standard generative AI systems pose a severe liability in open-ended healthcare queries due to high hallucination rates on poor-quality visual inputs.

This project introduces a **"Safe-Fail" architecture** that utilizes a Vision-Language Model (VLM) for macro-feature extraction (color, shape) but relies on **Human-in-the-Loop (HITL)** input and **deterministic database lookups** (FDA/NIH API) to establish absolute ground truth — completely mitigating the risk of AI-generated medical misinformation.

---

## System Architecture

The application pipeline is designed to gracefully handle uncertainty rather than forcing an automated guess.

| Phase | Component | Action | Output |
|-------|-----------|--------|--------|
| 1. Capture | UX ROI Overlay | Enforces a physical Region of Interest via front-facing camera, cropping a 224×224px image | `Base64 Cropped Image` |
| 2. Extraction | Vision-Language Model | Analyzes image **exclusively** for macro-physical attributes | `{"color": "white", "shape": "oval"}` |
| 3. Clarification | Human-in-the-Loop | Copilot prompts user to manually type the pill imprint | `{"imprint": "M365"}` |
| 4. Retrieval | Deterministic API | Queries NIH RxImage or FDA API using strict JSON parameters | `Factual Drug Data (JSON)` |
| 5. Synthesis | LLM Formatter | Translates raw API response into patient-friendly summary, citing source | `Final Copilot UI Message` |

---

## Engineering for Physical Constraints

OCR is notoriously brittle in edge healthcare deployments. Real-life patient captures frequently use low-resolution 2MP smartphone/web cameras where resolving a 2mm alphanumeric imprint on a curved, reflective white surface results in **optical smearing**.

By strictly limiting the vision model to **macro-feature extraction** (color and shape) and offloading **micro-feature extraction** (the imprint) to the user via a conversational Copilot interface, the system **circumvents the hardware limitation entirely**.

---

## AI Safety & Hallucination Mitigation

In consumer health products, an AI model that guesses incorrectly is fundamentally broken. This architecture implements a **zero-trust policy** for generative medical facts:

- **Restricted Prompting** — The VLM prompt is heavily constrained; it is explicitly forbidden from naming any medication based on the image alone.
- **Database Grounding** — The final output is a direct translation of a deterministic, federally regulated database response. If no match is found, the Copilot outputs a **safe refusal** rather than guessing a visually similar drug.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, Vanilla JS (mobile-responsive) |
| Edge Processing | HTML5 Canvas API (real-time video crop & bounding box) |
| Backend / Orchestration | Python FastAPI |
| AI Vision | GPT-4o-mini (macro-feature extraction only) |
| AI Synthesis | GPT-4o-mini (patient-friendly text formatting) |
| Ground Truth Data | NIH RxImage API + OpenFDA API |

---

## Project Structure

```
medication-id-copilot/
├── frontend/
│   ├── index.html          # Camera ROI overlay + chat UI
│   ├── app.js              # Canvas crop, API calls, conversation state
│   └── style.css           # Mobile-first responsive styles
├── backend/
│   ├── main.py             # FastAPI app — orchestration logic
│   ├── vlm_extractor.py    # GPT-4o-mini vision call (macro-features only)
│   ├── drug_lookup.py      # NIH RxImage + OpenFDA API clients
│   └── synthesizer.py      # LLM formatter for patient-friendly output
├── prompts/
│   ├── macro_extraction.txt   # VLM system prompt (restricted)
│   └── synthesis_formatter.txt # Final LLM synthesis prompt
├── docs/
│   └── architecture.md     # Detailed system design notes
├── .env.example
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- An OpenAI API key

### Installation

```bash
git clone https://github.com/mnouira02/medication-id-copilot.git
cd medication-id-copilot
pip install -r requirements.txt
cp .env.example .env   # Add your OpenAI API key
uvicorn backend.main:app --reload
```

Then open `frontend/index.html` in your browser.

---

## Safety Disclaimer

> ⚠️ This application is a **portfolio / research project** demonstrating safe AI architecture patterns. It is **not a certified medical device** and should not be used for actual medication decisions. Always consult a licensed pharmacist or physician.

---

## License

MIT — see [LICENSE](LICENSE)
