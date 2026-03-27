# Training Guide — Few-Shot MobileNetV2 Pipeline

## Overview

You only need **10 real photos** of the investigational product. The `augment.py` script applies 10 different image transforms in random combinations to generate **500+ training images** per class. This is a standard technique for few-shot fine-tuning and is well-suited to a clinical trial setting where you have exactly one physical pill.

---

## Folder Structure

```
training/
  data_raw/          ← your 10 real photos go here
    ip/
      ip_001.jpg
      ... (10 images)
    not_ip/
      not_ip_001.jpg
      ... (10 images)
  data/              ← augment.py writes here (500+ images)
    ip/
      orig_ip_001.jpg
      aug_ip_001_000.jpg
      aug_ip_001_001.jpg
      ... (500+ images)
    not_ip/
      ...
```

---

## Step 1 — Collect 10 Raw Photos

```bash
cd training/
pip install -r requirements.txt

python capture_tool.py --class ip       # 10 shots of the IP
python capture_tool.py --class not_ip   # 10 shots of background/wrong objects
```

The tool guides you through exactly what to shoot with on-screen prompts:

**IP shots (10 total):**
1. Top-down, well-lit
2. Slight left tilt
3. Slight right tilt
4. Close-up (fill the circle)
5. Further away
6. Dim lighting
7. Bright / backlit
8. Dark background
9. Light / white background
10. Held in palm of hand

**not_ip shots (10 total):**
1. Empty hand
2. Empty table
3. Different pill / wrong medication
4. Pen or small object
5. Finger covering ROI
6. Nothing in frame
7. Phone face-down
8. Different pill, dim lighting
9. Blurry / motion blur
10. Different pill, held in palm

---

## Step 2 — Augment (10 → 500+)

```bash
python augment.py
```

Each source image gets **50 augmented variants** using random combinations of:

| Transform | What it simulates |
|-----------|-------------------|
| `random_rotation` | Hand tilt during capture |
| `random_brightness` | Dim room to bright window |
| `random_contrast` | Overexposed vs flat camera |
| `random_blur` | 2MP camera focus blur |
| `random_noise` | Low-light sensor noise |
| `random_flip` | Different pill orientations |
| `random_zoom` | Distance variation |
| `random_hue_shift` | Colour temperature variation |
| `random_perspective` | Camera angle warp |
| `add_vignette` | Phone lens edge falloff |

Each augmented image applies **3–5 of these at random** so no two variants are identical.

Expected output:
```
[ip]     Found 10 source images. Generating 500 augmented images...
  ✅ 510 images written to data/ip/
[not_ip] Found 10 source images. Generating 500 augmented images...
  ✅ 510 images written to data/not_ip/
```

---

## Step 3 — Train

```bash
python train.py
```

The training runs in **two phases**:

**Phase 1** — Freeze entire MobileNetV2 base, train only the new classification head.
This converges fast and avoids overfitting on a small dataset.

**Phase 2** — Unfreeze the top 30 layers of the base and fine-tune at a very low learning rate (5e-5).
This lets the model adapt its high-level features to your specific IP appearance.

Expected output:
```
Phase 1: Training classification head (base frozen)...
Epoch 1/40 - loss: 0.68 - accuracy: 0.61 - val_auc: 0.74
...
Epoch 12/40 - loss: 0.18 - accuracy: 0.95 - val_auc: 0.98
Early stopping triggered.

Phase 2: Fine-tuning top 30 layers...
Epoch 1/40 - loss: 0.14 - accuracy: 0.96 - val_auc: 0.99
...

FINAL VALIDATION REPORT
ip       precision: 0.97  recall: 0.96
not_ip   precision: 0.96  recall: 0.97

False negative rate (missed IP):          4.0%
False positive rate (wrong pill accepted): 3.0%

✅ Done. Model exported to: ../frontend/public/model/
```

---

## Step 4 — Run the App

```bash
# Terminal 1
cd ../frontend && npm install && npm run dev      # localhost:3000

# Terminal 2
cd ../backend  && npm install && node server.js   # localhost:3001
```

Open `http://localhost:3000`. Hold the IP inside the circle — the diary unlocks at ≥90% confidence for 10 consecutive frames.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Val accuracy stuck at ~50% | More diversity in `not_ip` shots; add shots of similar-looking pills |
| Too many false negatives | Lower `CONF_THRESH` from 0.90 to 0.85 in `train.py` and `PillGate.jsx` |
| Training loss not decreasing | Increase `AUGS_PER_IMAGE` in `augment.py` to 80 |
| `model.pt not found` | You’re looking for the old PyTorch model — this pipeline outputs `model.json` |
