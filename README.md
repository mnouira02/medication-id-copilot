# 💊 Edge AI-Gated ePRO — Asynchronous Directly Observed Therapy (aDOT)

> **A privacy-first, browser-native clinical trial compliance system.** The patient's daily symptom diary is locked behind a computer vision gate that verifies the investigational product directly on the device. No video, no images, and no biometric data ever leaves the patient's device.

---

## Executive Summary

Medication non-adherence in Decentralized Clinical Trials (DCTs) compromises study integrity and costs sponsors millions. This project enforces **Asynchronous Directly Observed Therapy (aDOT)** using a lightweight MobileNetV2 model that runs entirely in the browser via **TensorFlow.js**.

The classifier answers exactly one question: **“Is this the investigational product?”** If yes, the ePRO diary unlocks. If not, the UI halts and a `prevented_dosing_error` telemetry event is logged to the backend audit trail. No images, no video, and no facial data ever leave the device.

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│          PATIENT DEVICE (all inference is local)    │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  WebRTC Camera Feed (getUserMedia)          │   │
│  │           ↓                                 │   │
│  │  Canvas API → 224×224 ROI Crop              │   │
│  │           ↓                                 │   │
│  │  Normalise: pixel / 255 → [0, 1]           │   │
│  │           ↓                                 │   │
│  │  TensorFlow.js — MobileNetV2 LayersModel    │   │
│  │  (model.json + shard bins, static files)    │   │
│  │           ↓                                 │   │
│  │  Softmax → class: ip / not_ip / background  │   │
│  │           ↓                                 │   │
│  │  Stable-frame debounce (N consecutive hits) │   │
│  └─────────────────────────────────────────────┘   │
│          ↓ ONLY this crosses the network ↓          │
└─────────────────────────────────────────────────────┘
                   ↓
  { event: "dose_verified", subject_id, timestamp, confidence }
  OR
  { event: "prevented_dosing_error", subject_id, timestamp }
                   ↓
┌──────────────────────┐
│  Node.js Telemetry   │
│  /api/log-adherence  │  ← Audit trail for clinical coordinators
└──────────────────────┘
```

---

## User Flow

1. Patient opens daily diary on phone or desktop browser
2. **ePRO diary is locked** — cannot submit without verification
3. Camera activates with circular ROI overlay (blurred outside, sharp inside)
4. Patient holds the IP inside the target circle
5. MobileNetV2 classifies continuously **locally in the browser via TensorFlow.js**
6. `ip` class with confidence ≥ 90% held for 10 consecutive frames → diary **unlocks** ✔️
7. Patient completes symptom questions and submits
8. Adherence event sent to backend — **no image, no video, no biometric data**
9. Wrong object held: diary stays locked, `prevented_dosing_error` logged ❌

---

## Technology Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| Frontend | Next.js (React) | ePRO state management, component-based diary |
| Edge AI | TensorFlow.js (WebGL + WASM fallback) | In-browser inference, no server round-trip |
| Model | MobileNetV2 3-class Keras (TFJS export) | < 10 MB, runs at ∼ 30fps on mobile CPU |
| Training | Python + Keras / TensorFlow | Fine-tunes on your IP photos, exports to TFJS format |
| Media | WebRTC getUserMedia + Canvas API | ROI crop + normalisation client-side |
| Backend | Node.js / Express | Lightweight telemetry endpoint only |
| Logging | SDTM-compatible JSONL | EX domain audit trail |

---

## Project Structure

```
medication-id-copilot/
├── training/                    # Python — run once to produce the TFJS model
│   ├── train.py                 # Keras MobileNetV2 fine-tune + TFJS export
│   ├── capture_tool.py          # Webcam tool to collect your own IP photos
│   ├── requirements.txt         # tensorflow, tensorflowjs, scikit-learn
│   └── data/
│       ├── ip/                  # ~150+ photos of the investigational product
│       ├── not_ip/              # ~150+ photos: other pills, hand, background
│       └── background/          # Plain empty-circle / table shots
├── frontend/                    # Next.js ePRO application
│   ├── public/
│   │   └── model/               # ← Drop exported model files here
│   │       ├── model.json       # TFJS model topology
│   │       ├── group1-shard*.bin # TFJS weight shards
│   │       └── class_map.json   # { "idx_to_class": { "0": "background", ... } }
│   ├── components/
│   │   ├── PillGate.jsx         # Camera + TF.js inference gate component
│   │   ├── DiaryForm.jsx        # Locked symptom diary (unlocks after gate)
│   │   └── ProgressBar.jsx
│   ├── pages/
│   │   └── index.jsx
│   └── styles/
│       └── PillGate.module.css
├── backend/                     # Node.js telemetry server (Express)
│   ├── server.js                # POST /api/log-adherence endpoint
│   ├── sdtm_logger.js           # SDTM EX domain JSONL writer
│   └── package.json
├── docs/
│   ├── architecture.md
│   ├── training_guide.md
│   └── privacy_compliance.md
└── README.md
```

---

## Quickstart

```bash
# 1. Train the model (CPU or GPU)
cd training/
pip install -r requirements.txt

# Organise your photos:
# training/data/ip/         ← investigational product
# training/data/not_ip/     ← other pills, empty hand, table
# training/data/background/ ← empty scene, circle with nothing

python train.py
# Outputs: frontend/public/model/model.json
#          frontend/public/model/group1-shard*.bin
#          frontend/public/model/class_map.json

# 2. Start the frontend
cd ../frontend
npm install
npm run dev        # http://localhost:3000

# 3. Start the backend (separate terminal)
cd ../backend
npm install
node server.js     # http://localhost:3001
```

---

## Model Training Notes

- **Architecture:** Keras MobileNetV2 pretrained on ImageNet, top 30 layers fine-tuned
- **Classes:** `ip` / `not_ip` / `background`
- **Normalisation:** `rescale=1/255` only — no ImageNet mean/std subtraction
- **Augmentation:** Random crop, flip, rotation, brightness/contrast
- **Two-phase training:** Head-only (40 epochs, frozen base) → fine-tune last 30 layers (40 epochs, early stopping)
- **Export:** `tensorflowjs.converters.save_keras_model` → `model.json` + `.bin` weight shards
- **Frontend inference:** `tf.loadLayersModel('/model/model.json')` → `model.predict(tensor)` with matching `pixel/255` normalisation

---

## Privacy & Regulatory Compliance

| Concern | This Architecture |
|---------|------------------|
| Patient video storage | ❌ Never stored — inference is local |
| PII transmission | ❌ Only subject_id + outcome event sent |
| HIPAA compliance | ✅ No PHI transmitted or stored server-side |
| GDPR Article 25 | ✅ Privacy by design — data minimisation |
| Audit trail | ✅ SDTM EX-compatible JSONL on backend |
| Regulatory grade | Portfolio / research prototype |

---

## Safety Disclaimer

> ⚠️ This is a **portfolio and research prototype** demonstrating clinical AI architecture for Decentralized Clinical Trials. It is not a validated eCOA system. Production deployment in a regulated trial requires 21 CFR Part 11 / ICH E6(R3) GCP validation.

---

## License

MIT
