# 💊 Edge AI-Gated ePRO — Asynchronous Directly Observed Therapy (aDOT)

> **A privacy-first, browser-native clinical trial compliance system.** The patient's daily symptom diary is locked behind a computer vision gate that verifies the investigational product directly on the device. No video ever leaves the patient's phone.

---

## Executive Summary

Medication non-adherence in Decentralized Clinical Trials (DCTs) compromises study integrity and costs sponsors millions. This project enforces **Asynchronous Directly Observed Therapy (aDOT)** using a lightweight MobileNetV2 model that runs entirely in the browser via **TensorFlow.js**.

The classifier answers exactly one binary question: **"Is this the investigational product?"** If yes, the ePRO diary unlocks. If not, the UI halts and a `prevented_dosing_error` telemetry event is logged to the backend audit trail. No images, no video, and no facial data ever leave the device.

---

## System Architecture

```
┌───────────────────────────────────────────────────┐
│         PATIENT DEVICE (Everything in ⬇️ is local)         │
│                                                               │
│  ┌───────────────────────────────────────────┐          │
│  │  WebRTC Camera Feed (getUserMedia)        │          │
│  │         ↓                                 │          │
│  │  Canvas API → 224×224 ROI Crop            │          │
│  │         ↓                                 │          │
│  │  TensorFlow.js MobileNetV2 Inference       │          │
│  │  (model weights served as static files)   │          │
│  │         ↓                                 │          │
│  │  Binary Result: IP_DETECTED / NOT_IP      │          │
│  └───────────────────────────────────────────┘          │
│          ↓ ONLY this crosses the network ↓                │
└───────────────────────────────────────────────────┘
                   ↓
  { dose_verified: true, subject_id, timestamp, confidence }
  OR
  { event: "prevented_dosing_error", subject_id, timestamp }
                   ↓
┌─────────────────────┐
│  Node.js Telemetry   │
│  /api/log-adherence  │  ← Audit trail for clinical coordinators
└─────────────────────┘
```

---

## User Flow

1. Patient opens daily diary on phone browser
2. **ePRO diary is locked** — cannot submit without verification
3. Camera activates with circular ROI overlay
4. Patient holds IP inside the target circle
5. MobileNetV2 classifies continuously at ~30fps **locally**
6. `IP_DETECTED` with confidence ≥90% → diary **unlocks** ✔️
7. Patient completes symptom questions and submits
8. Cryptographic adherence token sent to backend — **no image, no video**
9. If wrong object held: diary stays locked, `prevented_dosing_error` logged ❌

---

## Technology Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| Frontend | Next.js (React) | ePRO state management, component-based diary |
| Edge AI | TensorFlow.js (TFJS) | In-browser inference, zero data transfer |
| Model | MobileNetV2 (binary) | <5MB, 30fps on mobile CPU |
| Media | WebRTC getUserMedia + Canvas | ROI cropping without server round-trip |
| Backend | Node.js / Express | Lightweight telemetry endpoint |
| Training | Python + Keras/TF | Trains on your IP photos, exports to TFJS |
| Logging | SDTM-compatible JSONL | EX domain audit trail |

---

## Project Structure

```
medication-id-copilot/
├── training/                    # Python — run once to create the model
│   ├── train.py                 # MobileNetV2 fine-tune + TFJS export
│   ├── capture_tool.py          # Webcam tool to collect your own IP photos
│   ├── requirements.txt         # tensorflow, tensorflowjs, opencv-python
│   └── data/
│       ├── ip/                  # Your photos of the investigational product
│       └── not_ip/              # Background / wrong pills / hand / empty
├── frontend/                    # Next.js ePRO application
│   ├── public/
│   │   └── model/               # ← Drop your exported TFJS model here
│   │       ├── model.json
│   │       └── group1-shard1of1.bin
│   ├── components/
│   │   ├── PillGate.jsx         # Camera + TFJS inference gate component
│   │   ├── DiaryForm.jsx        # Locked symptom diary (unlocks after gate)
│   │   └── ProgressBar.jsx
│   ├── pages/
│   │   └── index.jsx            # Main ePRO page
│   ├── package.json
│   └── .env.local.example
├── backend/                     # Node.js telemetry server
│   ├── server.js                # Express: /api/log-adherence
│   ├── sdtm_logger.js           # SDTM EX domain JSONL writer
│   └── package.json
├── docs/
│   ├── architecture.md
│   ├── training_guide.md        # Step-by-step: collect photos → train → deploy
│   └── privacy_compliance.md    # HIPAA/GDPR zero-data-transfer rationale
└── README.md
```

---

## Training Your Own Model

See [`docs/training_guide.md`](docs/training_guide.md) for the full step-by-step.

**TL;DR:**
```bash
cd training/
pip install -r requirements.txt

# Step 1: Collect photos of your IP (or use capture_tool.py)
# training/data/ip/       ← ~150 photos of the investigational product
# training/data/not_ip/   ← ~150 photos of background, hand, wrong pills

# Step 2: Train + export to TensorFlow.js
python train.py
# Outputs: frontend/public/model/model.json + .bin shards

# Step 3: Start the app
cd ../frontend && npm install && npm run dev
cd ../backend  && npm install && node server.js
```

---

## Privacy & Regulatory Compliance

| Concern | This Architecture |
|---------|------------------|
| Patient video storage | ❌ Never stored — inference is local |
| PII transmission | ❌ Only subject_id + outcome hash sent |
| HIPAA compliance | ✅ No PHI transmitted or stored server-side |
| GDPR Article 25 | ✅ Privacy by design — data minimization |
| Audit trail | ✅ SDTM EX-compatible JSONL on backend |
| Regulatory grade | Portfolio/research prototype. Production use requires 21 CFR Part 11 validation. |

---

## Safety Disclaimer

> ⚠️ This is a **portfolio and research prototype** demonstrating clinical AI architecture for Decentralized Clinical Trials. It is not a validated eCOA system. Production deployment in a regulated trial requires 21 CFR Part 11 / ICH E6(R3) GCP validation.

---

## License
MIT
