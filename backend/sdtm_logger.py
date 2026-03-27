import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_exposure(study_id: str, subject_id: str, treatment: str, ndc: str):
    """
    SDTM EX Domain — Exposure event.
    Records verified pill ingestion with timestamp.
    """
    record = {
        "STUDYID": study_id,
        "DOMAIN": "EX",
        "USUBJID": subject_id,
        "EXSEQ": str(uuid.uuid4()),
        "EXTRT": treatment,
        "EXNDC": ndc,
        "EXSTDTC": _now(),
        "EXSTAT": "VERIFIED_BY_CNN",
        "EXMETHOD": "WEBCAM_CNN_CLASSIFICATION"
    }
    _append_log("EX", subject_id, record)


def log_questionnaire(study_id: str, subject_id: str, qstest: str, qsorres: str):
    """
    SDTM QS Domain — Questionnaire response.
    Records a single SMAQ question answer.
    """
    record = {
        "STUDYID": study_id,
        "DOMAIN": "QS",
        "USUBJID": subject_id,
        "QSSEQ": str(uuid.uuid4()),
        "QSCAT": "SMAQ",
        "QSTEST": qstest,
        "QSORRES": qsorres,
        "QSDTC": _now()
    }
    _append_log("QS", subject_id, record)


def _append_log(domain: str, subject_id: str, record: dict):
    log_file = LOG_DIR / f"{domain}_{subject_id}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")
