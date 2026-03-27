const fs   = require('fs');
const path = require('path');
const crypto = require('crypto');

const LOG_DIR = path.join(__dirname, 'logs');
if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR);

/**
 * Writes a single SDTM-compatible record to a JSONL audit log.
 *
 * EX domain: dose_verified events
 * QS domain: diary_submitted events (questionnaire responses)
 */
function logAdherenceEvent(payload) {
  const { subject_id, event, timestamp, domain } = payload;

  let record;

  if (event === 'dose_verified' || event === 'prevented_dosing_error') {
    // SDTM EX Domain — Exposure
    record = {
      STUDYID:  process.env.TRIAL_ID || 'TRIAL-001',
      DOMAIN:   'EX',
      USUBJID:  subject_id,
      EXSEQ:    crypto.randomUUID(),
      EXEVENT:  event,
      EXSTAT:   event === 'dose_verified' ? 'VERIFIED_BY_EDGE_CNN' : 'PREVENTED_DOSING_ERROR',
      EXCONF:   payload.confidence ?? null,
      EXMETHOD: 'TFJS_MOBILENETV2_EDGE_INFERENCE',
      EXSTDTC:  timestamp
    };
  } else if (event === 'diary_submitted') {
    // SDTM QS Domain — Questionnaire
    record = {
      STUDYID: process.env.TRIAL_ID || 'TRIAL-001',
      DOMAIN:  'QS',
      USUBJID: subject_id,
      QSSEQ:   crypto.randomUUID(),
      QSCAT:   'SMAQ',
      QSORRES: payload.responses,
      QSDTC:   timestamp
    };
  } else {
    record = { STUDYID: 'TRIAL-001', DOMAIN: 'AUDIT', USUBJID: subject_id, ...payload };
  }

  const domainKey = record.DOMAIN || 'AUDIT';
  const logFile   = path.join(LOG_DIR, `${domainKey}_${subject_id}.jsonl`);
  fs.appendFileSync(logFile, JSON.stringify(record) + '\n');
}

module.exports = { logAdherenceEvent };
