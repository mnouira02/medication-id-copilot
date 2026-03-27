# Training Guide — MobileNetV2 Binary Classifier

## Overview

You are training a **binary classifier** that answers one question:
> "Is the investigational product (IP) present in this image? Yes or No."

This is a closed-world, two-class problem. You do NOT need thousands of images. 150 per class is sufficient for fine-tuning MobileNetV2 on a problem this constrained.

---

## Step 1 — Collect Training Images

Use the built-in capture tool. It overlays the same ROI circle the app uses, so your training images match your inference conditions exactly.

```bash
cd training/
pip install -r requirements.txt

# Collect ~150 photos of the investigational product
python capture_tool.py --class ip

# Collect ~150 photos of background / wrong pills / hand / empty table
python capture_tool.py --class not_ip
```

**Tips for robust training data:**
- Vary **lighting**: bright room, dim room, window light, phone torch
- Vary **angle**: top-down, slight tilt, close-up, slightly blurry
- Vary **background**: table, palm of hand, white surface, dark surface
- For `not_ip`: include other pills, an empty hand, a pen, nothing in frame
- Do NOT include faces or PII in training images

Your folder structure after capture:
```
training/data/
  ip/
    ip_1710000000001.jpg
    ip_1710000000002.jpg
    ... (150+ images)
  not_ip/
    not_ip_1710000000001.jpg
    ... (150+ images)
```

---

## Step 2 — Train

```bash
cd training/
python train.py
```

Expected output:
```
Classes: {'ip': 0, 'not_ip': 1}
Epoch 1/30 — loss: 0.62, accuracy: 0.65, val_auc: 0.71
Epoch 5/30 — loss: 0.31, accuracy: 0.88, val_auc: 0.94
...
Epoch 14/30 — loss: 0.11, accuracy: 0.97, val_auc: 0.99
Early stopping triggered.

--- Validation Report ---
              precision  recall  f1-score
ip               0.97    0.96      0.97
not_ip           0.96    0.97      0.97

✅ Done. Model exported to: ../frontend/public/model/
```

Training time: ~5–10 min on CPU, ~2 min on GPU.

---

## Step 3 — Verify the Export

After training you should see:
```
frontend/public/model/
  model.json
  group1-shard1of1.bin   (~5MB)
  class_map.json         {"0": "ip", "1": "not_ip"}
```

These files are served as static assets by Next.js and loaded directly into the browser by TensorFlow.js — **no backend inference, no API call**.

---

## Step 4 — Run the Full Stack

```bash
# Terminal 1 — Frontend
cd frontend/
npm install
npm run dev
# → http://localhost:3000

# Terminal 2 — Telemetry backend
cd backend/
npm install
node server.js
# → http://localhost:3001
```

Open http://localhost:3000 in Chrome. Allow camera. Hold the IP inside the circle. The diary unlocks when confidence ≥ 90% for 10 consecutive frames (~300ms).

---

## Confidence Threshold

The threshold is set to **0.90** in both `training/train.py` and `frontend/components/PillGate.jsx`. You can tune this:
- Lower (e.g. 0.80): easier to trigger, more false positives
- Higher (e.g. 0.95): harder to trigger, more false negatives on poor cameras

For a clinical trial, **0.90 is the recommended floor**.
