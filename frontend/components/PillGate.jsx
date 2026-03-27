import { useEffect, useRef, useState } from "react";
import * as tf from "@tensorflow/tfjs";
import styles from "../styles/PillGate.module.css";

const API_BASE  = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:3001";
const MODEL_URL = "/model/model.json"; // TensorFlow.js LayersModel (Keras export)
const META_URL  = "/model/class_map.json";

// Confidence thresholds per class — must match training/train.py meta export
const THRESHOLDS = { background: 0.70, not_ip: 0.85, ip: 0.90 };
// Consecutive confident frames required before committing a state change
const STABLE     = { background: 6,    not_ip: 8,    ip: 10    };

/**
 * Crops a 224x224 canvas to a normalised [1,224,224,3] float32 tensor.
 * Normalisation: pixel / 255 only — matches Keras ImageDataGenerator rescale=1/255.
 * No ImageNet mean/std subtraction (that would be for PyTorch pretrained pipelines).
 */
function canvasToTensor(canvas) {
  return tf.tidy(() => {
    const imageTensor = tf.browser.fromPixels(canvas);          // [224,224,3] uint8
    const floatTensor = imageTensor.toFloat().div(tf.scalar(255)); // [224,224,3] 0-1
    return floatTensor.expandDims(0);                            // [1,224,224,3]
  });
}

// Optional pixel-level hue gate — secondary colour check on top of CNN prediction
function getRoiDominantColor(canvas) {
  const ctx    = canvas.getContext("2d");
  const pixels = ctx.getImageData(80, 80, 64, 64).data;
  let rSum = 0, gSum = 0, bSum = 0, count = 0;

  for (let i = 0; i < pixels.length; i += 4) {
    rSum += pixels[i];
    gSum += pixels[i + 1];
    bSum += pixels[i + 2];
    count++;
  }

  const r = rSum / count, g = gSum / count, b = bSum / count;
  if (r > g + 30 && r > b + 30) return "red";
  if (b > r + 30 && b > g + 10) return "blue";
  if (g > r + 20 && g > b + 20) return "green";
  if (r > 180 && g > 180 && b > 180) return "white";
  if (r > 180 && g > 150 && b < 100) return "yellow";
  return "other";
}

/**
 * PillGate — camera-based investigational product verification gate.
 *
 * Props:
 *   subjectId  {string}  — trial subject identifier, included in all log events
 *   onVerified {fn}      — called with { predictedClass, confidence } on success
 *   disabled   {bool}    — pauses inference loop when true
 *   ipColor    {string}  — optional dominant color hint ("blue"|"red"|"white"|...)
 *                          enables pixel-level hue gate as a secondary check
 */
export default function PillGate({ subjectId, onVerified, disabled, ipColor = null }) {
  const videoRef         = useRef(null); // blurred background video
  const videoSharpRef    = useRef(null); // sharp foreground video (CSS clip-path circle)
  const cropCanvasRef    = useRef(null); // hidden 224x224 canvas used for inference
  const overlayCanvasRef = useRef(null); // visible canvas — draws glowing ring only
  const modelRef         = useRef(null); // tf.LayersModel
  const metaRef          = useRef(null); // class_map.json { idx_to_class }
  const rafRef           = useRef(null); // requestAnimationFrame handle
  const streamRef        = useRef(null); // MediaStream reference
  const lastLoggedRef    = useRef("");   // deduplicates repeated logEvent calls
  const currentStatusRef = useRef("idle");

  // Per-class stable frame counters
  const stableIpRef         = useRef(0);
  const stableBackgroundRef = useRef(0);
  const stableWrongRef      = useRef(0);

  const [status,     setStatus]     = useState("loading");
  const [message,    setMessage]    = useState("Loading local model...");
  const [confidence, setConfidence] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        // Load TensorFlow.js LayersModel (exported by training/train.py)
        modelRef.current = await tf.loadLayersModel(MODEL_URL);

        // Warm up the model — first inference is always slow due to WASM JIT
        const warmup = tf.zeros([1, 224, 224, 3]);
        modelRef.current.predict(warmup).dispose();
        warmup.dispose();

        // Load class index map
        const metaRes = await fetch(META_URL);
        metaRef.current = await metaRes.json();

        // Start webcam stream
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width:  { ideal: 1280, max: 1920 },
            height: { ideal: 720,  max: 1080 }
          },
          audio: false
        });
        streamRef.current = stream;

        // Attach stream to both video elements (blurred + sharp)
        if (videoRef.current)      videoRef.current.srcObject      = stream;
        if (videoSharpRef.current) videoSharpRef.current.srcObject = stream;

        if (videoRef.current) {
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
      streamRef.current?.getTracks().forEach((t) => t.stop());
      // Clean up TF tensors on unmount
      modelRef.current?.dispose();
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
    } catch { /* backend offline during dev — non-fatal */ }
  }

  function drawOverlay(color = "#9ca3af") {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;

    const rect    = canvas.parentElement.getBoundingClientRect();
    canvas.width  = rect.width  * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;

    const ctx = canvas.getContext("2d");
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w  = rect.width;
    const h  = rect.height;
    const cx = w / 2;
    const cy = h / 2;

    // Radius matches CSS clip-path: circle(28%) which uses the diagonal
    const radius = 0.28 * (Math.sqrt(w * w + h * h) / Math.SQRT2);

    ctx.clearRect(0, 0, w, h);

    // Glowing ring only — blur handled by CSS dual-video layers
    ctx.strokeStyle = color;
    ctx.lineWidth   = 4;
    ctx.shadowColor = color;
    ctx.shadowBlur  = 10;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.shadowBlur = 0;
  }

  function tick() {
    rafRef.current = requestAnimationFrame(async () => {
      const video      = videoRef.current;
      const cropCanvas = cropCanvasRef.current;
      const model      = modelRef.current;
      const meta       = metaRef.current;

      if (!video || !cropCanvas || !model || !meta || disabled) {
        tick();
        return;
      }

      // Crop square ROI from centre of live video frame
      const ctx     = cropCanvas.getContext("2d");
      cropCanvas.width  = 224;
      cropCanvas.height = 224;

      const vw      = video.videoWidth;
      const vh      = video.videoHeight;
      const roiSize = Math.floor(Math.min(vw, vh) * 0.55);
      const sx      = (vw - roiSize) / 2;
      const sy      = (vh - roiSize) / 2;
      ctx.drawImage(video, sx, sy, roiSize, roiSize, 0, 0, 224, 224);

      // Run TF.js inference — tensor lifecycle managed inside canvasToTensor
      const inputTensor = canvasToTensor(cropCanvas);
      const outputTensor = modelRef.current.predict(inputTensor);
      const probs = await outputTensor.data(); // Float32Array of length num_classes
      inputTensor.dispose();
      outputTensor.dispose();

      const maxProb        = Math.max(...probs);
      const predIdx        = probs.indexOf(maxProb);
      const predictedClass = meta.idx_to_class[String(predIdx)];

      setConfidence(Math.round(maxProb * 100));

      // Optional hue gate — overrides "ip" if pixel colour doesn't match ipColor prop
      let classVote = predictedClass;
      if (ipColor && predictedClass === "ip") {
        const detectedColor = getRoiDominantColor(cropCanvas);
        if (detectedColor !== ipColor) classVote = "not_ip";
      }

      // Increment winning counter, slowly decay the others
      const confident = maxProb >= (THRESHOLDS[classVote] ?? 0.90);

      if (confident && classVote === "ip") {
        stableIpRef.current         += 1;
        stableBackgroundRef.current  = Math.max(0, stableBackgroundRef.current - 1);
        stableWrongRef.current       = Math.max(0, stableWrongRef.current - 1);
      } else if (confident && classVote === "background") {
        stableBackgroundRef.current += 1;
        stableIpRef.current          = Math.max(0, stableIpRef.current - 1);
        stableWrongRef.current       = Math.max(0, stableWrongRef.current - 1);
      } else if (confident && classVote === "not_ip") {
        stableWrongRef.current      += 1;
        stableIpRef.current          = Math.max(0, stableIpRef.current - 1);
        stableBackgroundRef.current  = Math.max(0, stableBackgroundRef.current - 1);
      } else {
        // Below threshold — decay all counters
        stableIpRef.current         = Math.max(0, stableIpRef.current - 1);
        stableBackgroundRef.current = Math.max(0, stableBackgroundRef.current - 1);
        stableWrongRef.current      = Math.max(0, stableWrongRef.current - 1);
      }

      // Commit state when counter crosses its threshold
      if (stableIpRef.current >= STABLE.ip) {
        currentStatusRef.current = "good";
      } else if (stableWrongRef.current >= STABLE.not_ip) {
        currentStatusRef.current = "wrong";
      } else if (stableBackgroundRef.current >= STABLE.background) {
        currentStatusRef.current = "idle";
      } else {
        currentStatusRef.current = "analyzing";
      }

      const committed = currentStatusRef.current;

      const overlayColor = {
        good:      "#22c55e",
        wrong:     "#ef4444",
        idle:      "#9ca3af",
        analyzing: "#f59e0b"
      }[committed];

      drawOverlay(overlayColor);

      if (committed === "idle") {
        setStatus("idle");
        setMessage("Place the pill inside the circle.");

      } else if (committed === "wrong") {
        setStatus("wrong");
        setMessage("This is not the correct pill.");
        await logEvent("prevented_dosing_error", {
          predicted_class: "not_ip",
          confidence: Number(maxProb.toFixed(4))
        });

      } else if (committed === "good") {
        const progress = Math.min(stableIpRef.current, STABLE.ip);
        setStatus("good");
        setMessage(`Correct pill detected. Hold steady... ${progress}/${STABLE.ip}`);

        if (stableIpRef.current >= STABLE.ip) {
          setMessage("Correct pill confirmed. Unlocking...");
          await onVerified({
            predictedClass: "ip",
            confidence: Number(maxProb.toFixed(4))
          });
          return; // stop the loop — diary is unlocked
        }

      } else {
        setStatus("analyzing");
        setMessage("Analyzing...");
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

      <div className={`${styles.cameraCard} ${status === "wrong" ? styles.shake : ""}`}>

        {/* Layer 1 — blurred background: CSS filter on native video, no canvas required */}
        <video ref={videoRef} autoPlay playsInline muted
          className={`${styles.video} ${styles.videoBlurred}`} />

        {/* Layer 2 — sharp foreground: same stream, CSS clip-path cuts the circle */}
        <video ref={videoSharpRef} autoPlay playsInline muted
          className={`${styles.video} ${styles.videoSharp}`} />

        {/* Layer 3 — glowing ring: canvas draws stroke only, no video pixels */}
        <canvas ref={overlayCanvasRef} className={styles.overlayCanvas} />

        <div className={`${styles.statusPill} ${
          status === "good"      ? styles.green  :
          status === "wrong"     ? styles.red    :
          status === "analyzing" ? styles.amber  : styles.grey
        }`}>
          {status === "good"      ? "Correct pill" :
           status === "wrong"     ? "Wrong pill"   :
           status === "analyzing" ? "Analyzing"    : "Waiting"}
        </div>
      </div>

      {/* Hidden crop canvas — used for inference only, never shown */}
      <canvas ref={cropCanvasRef} style={{ display: "none" }} />

      <div className={styles.feedbackCard}>
        <p className={styles.message}>{message}</p>
        <div className={styles.confidenceTrack}>
          <div
            className={`${styles.confidenceFill} ${
              status === "good"      ? styles.greenFill :
              status === "wrong"     ? styles.redFill   :
              status === "analyzing" ? styles.amberFill : styles.greyFill
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
