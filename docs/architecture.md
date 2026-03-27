# System Design Notes — Medication ID Copilot

## Design Philosophy

The core principle of this system is that **AI should never be the source of medical ground truth**. The generative model acts as a UX facilitator (extracting visual features and formatting text), while a federally regulated deterministic API holds all clinical authority.

## Phase-by-Phase Decision Log

### Phase 1 — ROI Enforcement
A fixed 224×224px crop is used deliberately. This matches the input resolution of common vision model benchmarks and forces the camera operator (patient) to physically center the pill, reducing background noise that would confuse the VLM.

### Phase 2 — Macro-Only VLM
The system prompt uses both positive and negative constraints. Positive: return a JSON with color, shape, scoring, and surface. Negative: explicitly forbidden from naming any drug. Temperature is set to 0.0 to eliminate stochastic variation. `response_format: json_object` is used to guarantee parseable output.

### Phase 3 — Human-in-the-Loop Imprint
Imprint recognition via OCR on a 2MP camera is too unreliable for safety-critical applications. Delegating this to the user converts an unreliable AI task into a trivial human reading task, eliminating the failure mode entirely.

### Phase 4 — NIH RxImage API
The NIH RxImage API (https://rximage.nlm.nih.gov/) is a free, publicly available federal database containing pill images and attributes indexed by color, shape, and imprint. This is the canonical source. No AI model can be more authoritative than a federal drug registry.

### Phase 5 — Synthesis Formatter
The LLM at this stage is functioning as a **text formatter**, not a knowledge source. It receives a structured fact block and is constrained to only reformat those facts. The system prompt explicitly forbids adding side effects, dosage information, or clinical recommendations.

## Failure Modes and Mitigations

| Failure Mode | Mitigation |
|---|---|
| Low-quality image | ROI crop + macro-only VLM (not OCR) |
| VLM hallucinates drug name | System prompt hard-blocks drug naming |
| No API match | Safe refusal message, directs to pharmacist |
| API downtime | HTTP timeout handling + graceful error message |
| Imprint typo by user | User can re-submit; no penalty for retry |
