import { useEffect, useRef, useState } from "react";
import * as tf from "@tensorflow/tfjs";
import styles from "../styles/PillGate.module.css";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:3001";
const MODEL_URL = "/model/model.json";
const META_URL = "/model/class_map.json";

export default function PillGate({ subjectId, onVerified, disabled }) {
  const videoRef = useRef(null);
  const cropCanvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const modelRef = useRef(null);
  const metaRef = useRef(null);
  const rafRef = useRef(null);
  const streamRef = useRef(null);
  const stableIpRef = useRef(0);
  const lastLoggedRef = useRef("");

  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("Loading local model...");
  const [confidence, setConfidence] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        modelRef.current = await tf.loadLayersModel(MODEL_URL);
        const metaRes = await fetch(META_URL);
        metaRef.current = await metaRes.json();

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 1280 } },
          audio: false
        });
        streamRef.current = stream;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await new Promise((resolve) =>
            videoRef.current.addEventListener("loadeddata", resolve, { once: true })
          );
        }

        if (!cancelled) {
          setStatus("idle");
          setMessage("Place the pill inside the circle.");
          tick();
        }
      } catch (err) {
        setStatus("error");
        setMessage(`Camera or model error: ${err.message}`);
      }
    }

    init();

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  async function logEvent(event, payload = {}) {
    try {
      const key = `${event}:${payload.predicted_class || ""}`;
      if (event === "prevented_dosing_error" && lastLoggedRef.current === key) return;
      lastLoggedRef.current = key;

      await fetch(`${API_BASE}/api/log-adherence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_id: subjectId,
          event,
          timestamp: new Date().toISOString(),
          ...payload
        })
      });
    } catch { }
  }

  function drawOverlay(color = "#9ca3af") {
    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const rect = video.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;

    const ctx = canvas.getContext("2d");
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w = rect.width;
    const h = rect.height;
    const radius = Math.min(w, h) * 0.28;
    const cx = w / 2;
    const cy = h / 2;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "rgba(0,0,0,0.45)";
    ctx.fillRect(0, 0, w, h);

    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();
  }

  function tick() {
    rafRef.current = requestAnimationFrame(async () => {
      const video = videoRef.current;
      const cropCanvas = cropCanvasRef.current;
      const model = modelRef.current;
      const meta = metaRef.current;

      if (!video || !cropCanvas || !model || !meta || disabled) {
        tick();
        return;
      }

      const ctx = cropCanvas.getContext("2d");
      cropCanvas.width = 224;
      cropCanvas.height = 224;

      const vw = video.videoWidth;
      const vh = video.videoHeight;
      const roiSize = Math.floor(Math.min(vw, vh) * 0.55);
      const sx = (vw - roiSize) / 2;
      const sy = (vh - roiSize) / 2;

      ctx.drawImage(video, sx, sy, roiSize, roiSize, 0, 0, 224, 224);

      const tensor = tf.browser
        .fromPixels(cropCanvas)
        .toFloat()
        .div(255)
        .expandDims(0);

      const pred = model.predict(tensor);
      const data = await pred.data();

      tensor.dispose();
      pred.dispose();

      const probs = Array.from(data);
      const maxProb = Math.max(...probs);
      const predIdx = probs.indexOf(maxProb);
      const predictedClass = meta.idx_to_class[String(predIdx)] || meta.idx_to_class[predIdx];

      setConfidence(Math.round(maxProb * 100));

      if (predictedClass === "background" && maxProb >= 0.7) {
        stableIpRef.current = 0;
        setStatus("idle");
        setMessage("Please place the pill inside the circle.");
        drawOverlay("#9ca3af");
      } else if (predictedClass === "not_ip" && maxProb >= 0.85) {
        stableIpRef.current = 0;
        setStatus("wrong");
        setMessage("This is not the correct pill.");
        drawOverlay("#ef4444");
        await logEvent("prevented_dosing_error", {
          predicted_class: "not_ip",
          confidence: Number(maxProb.toFixed(4))
        });
      } else if (predictedClass === "ip" && maxProb >= 0.9) {
        stableIpRef.current += 1;
        setStatus("good");
        setMessage(`Correct pill detected. Hold steady... ${stableIpRef.current}/8`);
        drawOverlay("#22c55e");

        if (stableIpRef.current >= 8) {
          setMessage("Correct pill confirmed. Unlocking...");
          await onVerified({
            predictedClass: "ip",
            confidence: Number(maxProb.toFixed(4))
          });
          return;
        }
      } else {
        stableIpRef.current = 0;
        setStatus("analyzing");
        setMessage("Pill detected. Analyzing...");
        drawOverlay("#f59e0b");
      }

      tick();
    });
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.copy}>
        <span className={styles.badge}>Medication check</span>
        <h2 className={styles.title}>Show the pill provided by the investigator</h2>
        <p className={styles.subtitle}>
          Keep the pill inside the circle. The app checks the cropped ROI locally on your device.
        </p>
      </div>

      <div
        className={`${styles.cameraCard} ${status === "wrong" ? styles.shake : ""
          }`}
      >
        <video ref={videoRef} autoPlay playsInline muted className={styles.video} />
        <canvas ref={overlayCanvasRef} className={styles.overlayCanvas} />
        <div
          className={`${styles.statusPill} ${status === "good"
              ? styles.green
              : status === "wrong"
                ? styles.red
                : status === "analyzing"
                  ? styles.amber
                  : styles.grey
            }`}
        >
          {status === "good"
            ? "Correct pill"
            : status === "wrong"
              ? "Wrong pill"
              : status === "analyzing"
                ? "Analyzing"
                : "Waiting"}
        </div>
      </div>

      <canvas ref={cropCanvasRef} style={{ display: "none" }} />

      <div className={styles.feedbackCard}>
        <p className={styles.message}>{message}</p>
        <div className={styles.confidenceTrack}>
          <div
            className={`${styles.confidenceFill} ${status === "good"
                ? styles.greenFill
                : status === "wrong"
                  ? styles.redFill
                  : status === "analyzing"
                    ? styles.amberFill
                    : styles.greyFill
              }`}
            style={{ width: `${confidence}%` }}
          />
        </div>
        <div className={styles.confidenceRow}>
          <span>Model confidence</span>
          <strong>{confidence}%</strong>
        </div>
      </div>
    </div>
  );
}