# 💊 Edge AI-Gated ePRO — Asynchronous Directly Observed Therapy (aDOT)

> **A privacy-first, browser-native clinical trial compliance system.** The patient's daily symptom diary is locked behind a computer vision gate that verifies the investigational product directly on the device. No video, no images, and no biometric data ever leaves the patient's device.

---

## Executive Summary

Medication non-adherence in Decentralized Clinical Trials (DCTs) compromises study integrity and costs sponsors millions. This project enforces **Asynchronous Directly Observed Therapy (aDOT)** using a lightweight MobileNetV2 model that runs entirely in the browser via **ONNX Runtime Web (WASM)**.

The classifier answers exactly one question: **"Is this the investigational product?"** If yes, the ePRO diary unlocks. If not, the UI halts and a `prevented_dosing_error` telemetry event is logged to the backend audit trail. No images, no video, and no facial data ever leave the device.

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
│  │  ImageNet Normalisation (mean/std)          │   │
│  │           ↓                                 │   │
│  │  ONNX Runtime Web — MobileNetV2 WASM        │   │
│  │  (model.onnx served as a static file)       │   │
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
5. MobileNetV2 classifies continuously **locally in the browser**
6. `ip` class with confidence ≥ 90% held for 10 consecutive frames → diary **unlocks** ✔️
7. Patient completes symptom questions and submits
8. Adherence event sent to backend — **no image, no video, no biometric data**
9. Wrong object held: diary stays locked, `prevented_dosing_error` logged ❌

---

## Technology Stack

| Layer | Technology | Reason |
|-------|------------|--------|
| Frontend | Next.js 16 (React) | ePRO state management, component-based diary |
| Edge AI | ONNX Runtime Web (WASM) | In-browser inference, no server round-trip, no WebGL dependency |
| Model | MobileNetV2 (3-class) | < 15 MB ONNX, fast on CPU/WASM |
| Training | PyTorch + torchvision | Fine-tunes on your IP photos, exports to ONNX |
| Media | WebRTC getUserMedia + Canvas | ROI crop + ImageNet normalisation client-side |
| Backend | Node.js / Express | Lightweight telemetry endpoint only |
| Logging | SDTM-compatible JSONL | EX domain audit trail |

---

## Project Structure

```
medication-id-copilot/
├── training/                    # Python — run once to produce model.onnx
│   ├── train.py                 # MobileNetV2 fine-tune (PyTorch) + ONNX export
│   ├── capture_tool.py          # Webcam tool to collect your own IP photos
│   ├── requirements.txt
│   └── data/
│       ├── ip/                  # ~150+ photos of the investigational product
│       ├── not_ip/              # ~150+ photos: background, wrong pills, hand, empty
│       └── background/          # Plain background / empty circle shots
├── frontend/                    # Next.js ePRO application
│   ├── public/
│   │   └── model/               # ← Drop your exported model files here
│   │       ├── model.onnx       # Exported from training/train.py
│   │       └── class_map.json   # { "idx_to_class": { "0": "background", ... } }
│   ├── components/
│   │   ├── PillGate.jsx         # Camera + ONNX RT inference gate component
│   │   ├── DiaryForm.jsx        # Locked symptom diary (unlocks after gate)
│   │   └── ProgressBar.jsx
│   ├── pages/
│   │   └── index.jsx
│   └── styles/
│       └── PillGate.module.css
├── backend/                     # Node.js telemetry server
│   ├── server.js                # Express: /api/log-adherence
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
# 1. Train the model (GPU recommended — RTX 2080+ or equivalent)
cd training/
pip install -r requirements.txt

# Collect photos of your IP:
# training/data/ip/         ← investigational product
# training/data/not_ip/     ← other pills, background, hand
# training/data/background/ ← empty scene

python train.py
# Outputs: training/model.onnx + frontend/public/model/class_map.json

# Copy model to frontend
copy model.onnx ..\frontend\public\model\model.onnx

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

- **Architecture:** MobileNetV2 pretrained on ImageNet, last 20 layers fine-tuned
- **Classes:** `ip` / `not_ip` / `background`
- **Augmentation:** Random crop, flip, rotation, brightness/contrast only
  - Saturation and hue jitter deliberately excluded to preserve colour discrimination
- **Two-phase training:** Head-only (40 epochs) → fine-tune last 20 layers (40 epochs, early stopping)
- **Inference:** ONNX exported with `opset_version=12`, loaded via `onnxruntime-web` WASM
- **Normalisation:** ImageNet mean/std applied client-side before inference

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
