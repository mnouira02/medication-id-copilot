# SDTM Logging Specification

## Overview

This system generates SDTM-compliant event logs for two domains: **EX** (Exposure) and **QS** (Questionnaire). Logs are written as JSONL files (one JSON object per line) to the `logs/` directory.

---

## EX Domain — Exposure

Triggered when a patient clicks "I have taken my medication" after successful CNN verification.

| Variable | Description | Example |
|----------|-------------|----------|
| STUDYID | Trial identifier | `TRIAL-001` |
| DOMAIN | Always `EX` | `EX` |
| USUBJID | Subject identifier | `SUBJ-042` |
| EXSEQ | Unique sequence UUID | `a3f...` |
| EXTRT | Treatment name | `Atorvastatin 20mg` |
| EXNDC | NDC code | `00071-0155` |
| EXSTDTC | ISO 8601 UTC timestamp | `2026-03-27T11:32:00Z` |
| EXSTAT | Verification status | `VERIFIED_BY_CNN` |
| EXMETHOD | Verification method | `WEBCAM_CNN_CLASSIFICATION` |

---

## QS Domain — Questionnaire

Triggered for each SMAQ question answered.

| Variable | Description | Example |
|----------|-------------|----------|
| STUDYID | Trial identifier | `TRIAL-001` |
| DOMAIN | Always `QS` | `QS` |
| USUBJID | Subject identifier | `SUBJ-042` |
| QSSEQ | Unique sequence UUID | `b7c...` |
| QSCAT | Questionnaire category | `SMAQ` |
| QSTEST | Question identifier | `SMAQ1` |
| QSORRES | Patient response | `No` |
| QSDTC | ISO 8601 UTC timestamp | `2026-03-27T11:31:00Z` |

---

## Integration Notes

- Logs are append-only JSONL files: `logs/EX_SUBJ-042.jsonl`, `logs/QS_SUBJ-042.jsonl`
- Compatible with Medidata Rave, Veeva Vault, and any CDISC-compliant EDC
- For production use, replace file logging with a secure database writer and encrypt PII fields
