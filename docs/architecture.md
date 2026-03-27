# System Design Notes — Clinical Trial Medication Compliance Verifier

## Design Philosophy

The core principle is **verified compliance at the point of care**. The system enforces a strict gate: a patient cannot advance past the pill verification step until the correct medication is confirmed by the CNN. No backend logic bypasses this.

## Phase-by-Phase Decision Log

### Phase 1 — SMAQ Questionnaire
The Simplified Medication Adherence Questionnaire (SMAQ) is a 6-item validated instrument. Responses are captured as structured JSON and written immediately to the SDTM QS domain log. The questionnaire must be completed before the pill verification step is accessible.

### Phase 2 — Custom CNN (not a general LLM)
A closed-world classifier is far more appropriate than a general VLM here because:
1. The trial protocol defines exactly which pills are valid (2–5 typically)
2. A ResNet18 classifier trained on those specific pills can achieve >94% accuracy
3. No external API call, no latency, no hallucination risk, no data privacy concerns
4. The model is retrained per trial by updating `config/protocol.json` and re-running `train_cnn.py`

### Phase 3 — Ingestion Confirmation (Human-in-the-Loop)
The CNN verifies the pill is correct but cannot verify ingestion. A mandatory confirmation button forces the patient to declare they have taken the medication. This event is logged to SDTM EX.

### Phase 4 — SDTM Logging
Two domains are written:
- **EX**: Records treatment name, NDC code, timestamp, and verification method (`WEBCAM_CNN_CLASSIFICATION`)
- **QS**: Records each SMAQ question response with a UTC timestamp

These JSONL files can be ingested by any CDISC-compliant EDC (e.g. Medidata Rave, Veeva Vault).

## Failure Modes and Mitigations

| Failure Mode | Mitigation |
|---|---|
| Wrong pill shown | CNN returns no_match → 400 response → frontend blocks progression |
| Low confidence prediction | Confidence threshold set to 0.85 — anything below triggers retry |
| Camera unavailable | Graceful error message; capture button disabled |
| Model not trained yet | `pill_classifier.py` returns safe placeholder with clear message |
| Patient skips confirmation | Confirm button only appears after CNN match; SDTM log not written until clicked |
| API downtime | Frontend catches fetch errors; patient instructed to retry |
