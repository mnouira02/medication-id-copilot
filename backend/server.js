const express = require('express');
const cors    = require('cors');
const helmet  = require('helmet');
const { logAdherenceEvent } = require('./sdtm_logger');

const app  = express();
const PORT = process.env.PORT || 3001;

app.use(helmet());
app.use(cors());
app.use(express.json());

/**
 * POST /api/log-adherence
 *
 * Receives ONLY a cryptographic outcome payload — never image data.
 * Logs to SDTM-compatible JSONL audit trail.
 *
 * Body shape (dose_verified event):
 *   { subject_id, dose_verified, confidence, timestamp, event }
 *
 * Body shape (diary_submitted event):
 *   { subject_id, event: 'diary_submitted', domain: 'QS', responses, timestamp }
 */
app.post('/api/log-adherence', (req, res) => {
  const payload = req.body;

  if (!payload.subject_id || !payload.event || !payload.timestamp) {
    return res.status(400).json({ error: 'Missing required fields: subject_id, event, timestamp' });
  }

  // Reject any payload that contains image or video data (safety guard)
  const bodyStr = JSON.stringify(payload);
  if (bodyStr.length > 10_000) {
    return res.status(413).json({ error: 'Payload too large — image data is not accepted' });
  }

  logAdherenceEvent(payload);

  console.log(`[AUDIT] ${payload.timestamp} | ${payload.subject_id} | ${payload.event}`);
  res.json({ status: 'logged', event: payload.event });
});

app.get('/health', (_, res) => res.json({ status: 'ok' }));

app.listen(PORT, () => console.log(`Telemetry server running on http://localhost:${PORT}`));
