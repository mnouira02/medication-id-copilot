import { useEffect, useRef, useState } from 'react';
import * as tf from '@tensorflow/tfjs';
import styles from '../styles/PillGate.module.css';

const MODEL_URL = '/model/model.json';
const CONF_THRESHOLD = 0.90;
const REQUIRED_CONSECUTIVE = 10; // must detect IP for 10 consecutive frames

export default function PillGate({ subjectId, onVerified }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const modelRef = useRef(null);
  const rafRef = useRef(null);
  const consecutiveRef = useRef(0);

  const [status, setStatus] = useState('loading'); // loading | ready | detecting | verified | error
  const [confidence, setConfidence] = useState(0);
  const [message, setMessage] = useState('Loading model...');

  useEffect(() => {
    let stream;

    async function init() {
      try {
        // Load TFJS model (weights are static files in /public/model/)
        modelRef.current = await tf.loadLayersModel(MODEL_URL);
        setMessage('Hold your medication inside the circle.');
        setStatus('ready');

        // Start camera
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 } }
        });
        videoRef.current.srcObject = stream;
        await new Promise(r => videoRef.current.addEventListener('loadeddata', r, { once: true }));

        setStatus('detecting');
        runInference();
      } catch (err) {
        setStatus('error');
        setMessage('Camera or model unavailable: ' + err.message);
      }
    }

    function runInference() {
      rafRef.current = requestAnimationFrame(async () => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas || !modelRef.current) return;

        const vw = video.videoWidth;
        const vh = video.videoHeight;
        const roiSize = Math.floor(Math.min(vw, vh) * 0.55);
        const sx = (vw - roiSize) / 2;
        const sy = (vh - roiSize) / 2;

        const ctx = canvas.getContext('2d');
        canvas.width = 224;
        canvas.height = 224;
        ctx.drawImage(video, sx, sy, roiSize, roiSize, 0, 0, 224, 224);

        // Run inference entirely on device — no network call
        const tensor = tf.browser.fromPixels(canvas)
          .toFloat()
          .div(255.0)
          .expandDims(0);

        const prediction = modelRef.current.predict(tensor);
        const score = (await prediction.data())[0]; // sigmoid output: 0=ip, 1=not_ip
        const ipConfidence = 1 - score;             // invert: high = IP detected

        tensor.dispose();
        prediction.dispose();

        setConfidence(Math.round(ipConfidence * 100));

        if (ipConfidence >= CONF_THRESHOLD) {
          consecutiveRef.current++;
          setMessage(`IP detected — hold steady (${consecutiveRef.current}/${REQUIRED_CONSECUTIVE})`);

          if (consecutiveRef.current >= REQUIRED_CONSECUTIVE) {
            // Log telemetry — ONLY the outcome, never the image
            await logAdherence(subjectId, true, ipConfidence);
            setStatus('verified');
            setMessage('Verified ✔️ Unlocking diary...');
            setTimeout(onVerified, 1000);
            return;
          }
        } else {
          if (consecutiveRef.current > 0) {
            // Dropped below threshold — log prevented error if it was a different object
            if (ipConfidence < 0.3) {
              await logAdherence(subjectId, false, ipConfidence);
            }
          }
          consecutiveRef.current = 0;
          setMessage('Hold your medication inside the circle.');
        }

        runInference();
      });
    }

    init();

    return () => {
      cancelAnimationFrame(rafRef.current);
      if (stream) stream.getTracks().forEach(t => t.stop());
    };
  }, []);

  async function logAdherence(subjectId, verified, conf) {
    // ONLY cryptographic outcome is sent — no image data
    try {
      await fetch('/api/log-adherence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject_id: subjectId,
          dose_verified: verified,
          confidence: Math.round(conf * 10000) / 10000,
          timestamp: new Date().toISOString(),
          event: verified ? 'dose_verified' : 'prevented_dosing_error'
        })
      });
    } catch { /* non-blocking */ }
  }

  return (
    <div className={styles.gate}>
      <p className={styles.instruction}>{message}</p>

      <div className={styles.cameraWrapper}>
        <video ref={videoRef} autoPlay playsInline muted className={styles.video} />
        <div className={`${styles.roiCircle} ${status === 'verified' ? styles.roiVerified : ''}`}>
          <span className={styles.roiLabel}>Place IP here</span>
        </div>
      </div>

      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {status === 'detecting' && (
        <div className={styles.confidenceBar}>
          <div className={styles.confidenceFill} style={{ width: `${confidence}%`,
            background: confidence >= 90 ? '#22c55e' : confidence >= 60 ? '#f59e0b' : '#ef4444'
          }} />
          <span className={styles.confidenceLabel}>{confidence}% IP confidence</span>
        </div>
      )}
    </div>
  );
}
