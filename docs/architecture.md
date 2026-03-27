# Architecture Decision Log — aDOT Edge AI ePRO

## Core Design Principle

**Zero Data Transfer.** No video frame, image, or biometric data ever leaves the patient's device. The only network call is a cryptographic JSON payload confirming the outcome of the classification.

## Why TensorFlow.js (not a server-side API)?

| Approach | Latency | Privacy | HIPAA/GDPR |
|---|---|---|---|
| Send image to backend API | 200–1000ms | ❌ PII transmitted | Requires BAA / DPA |
| Cloud Vision API | 300–1500ms | ❌ PII transmitted | Requires BAA / DPA |
| TFJS edge inference | <30ms | ✅ Nothing transmitted | No BAA needed |

## Why MobileNetV2 (not YOLO or ResNet50)?

- YOLO requires reliable bounding-box regression — brittle on 2MP blurry images
- ResNet50 is ~100MB — too large to serve as a static browser asset
- MobileNetV2 fine-tuned: ~5MB, 30fps on mobile CPU, >95% accuracy on binary IP/not-IP

## Why Binary Classification (not multi-class)?

The system does not need to identify *which* drug it is — the patient already knows their assigned treatment. It only needs to verify: **"Is this the correct study medication?"** Binary classification is simpler, more accurate, and more defensible than a multi-class approach for this problem.

## Why Affordance-Driven ROI (not object detection)?

Forcing the user to physically center the pill in the UI circle:
1. Guarantees the pill dominates the 224×224 crop
2. Eliminates the need for object detection on blurry consumer cameras
3. Reduces inference payload by >90% vs. processing the full 1080p frame
4. Runs at 30fps on mobile without thermal throttling

## Telemetry Payload Design

The backend receives ONLY:
```json
{
  "subject_id": "SUBJ-042",
  "event": "dose_verified",
  "dose_verified": true,
  "confidence": 0.9731,
  "timestamp": "2026-03-27T11:32:00Z"
}
```

No image. No video. No face. The backend enforces a payload size limit of 10KB to make it structurally impossible to submit image data.
