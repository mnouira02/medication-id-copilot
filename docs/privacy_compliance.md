# Privacy & Regulatory Compliance

## HIPAA Compliance

Traditional aDOT solutions require patients to record and upload videos of themselves taking medication. This creates significant HIPAA liabilities:
- Video feeds containing faces = biometric PII
- PHI stored on vendor servers requires a Business Associate Agreement (BAA)
- Data breach risk for sensitive health + biometric data

This architecture eliminates these risks entirely via **client-side inference**:
- Model weights are downloaded to the patient's device as static files
- All inference runs in the browser's JavaScript engine
- No video frame, image, or facial data is ever transmitted
- The server receives only: `{ subject_id, dose_verified: true, confidence, timestamp }`

## GDPR Article 25 — Privacy by Design

GDPR Article 25 requires "data protection by design and by default." This architecture satisfies this by:
- **Data minimisation**: only the minimum necessary data (outcome + timestamp) is transmitted
- **Purpose limitation**: the telemetry payload contains no data beyond its stated purpose
- **Storage limitation**: no biometric data is stored server-side

## 21 CFR Part 11 / ICH E6(R3) Note

This is a **research prototype**. Production deployment in a regulated clinical trial requires:
- Validation documentation (IQ/OQ/PQ)
- Audit trail tamper-proofing (currently append-only JSONL, needs cryptographic signing)
- Access controls and user authentication
- Integration with a validated EDC (e.g. Medidata Rave, Veeva Vault)
