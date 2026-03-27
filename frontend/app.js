const API_BASE = "http://localhost:8000";

// --- State ---
let questions = [];
let answers = {};
let currentQuestionIndex = 0;
let verifiedPillId = null;

// --- DOM ---
const progressBar = document.getElementById("progress-bar");
const progressLabel = document.getElementById("progress-label");

const stepQuestionnaire = document.getElementById("step-questionnaire");
const stepVerification = document.getElementById("step-verification");
const stepComplete = document.getElementById("step-complete");

const questionText = document.getElementById("question-text");
const answerOptions = document.getElementById("answer-options");
const questionCounter = document.getElementById("question-counter");

const video = document.getElementById("video");
const captureCanvas = document.getElementById("capture-canvas");
const captureBtn = document.getElementById("capture-btn");
const verificationResult = document.getElementById("verification-result");
const confirmBtn = document.getElementById("confirm-btn");

// --- Init ---
async function init() {
  await loadQuestionnaire();
  await startCamera();
  setProgress(5, "Step 1 of 3 — Questionnaire");
}

async function loadQuestionnaire() {
  const res = await fetch(`${API_BASE}/questionnaire`);
  const data = await res.json();
  questions = data.questions;
  showQuestion(0);
}

function setProgress(pct, label) {
  progressBar.style.width = pct + "%";
  progressLabel.textContent = label;
}

// --- STEP 1: Questionnaire ---
function showQuestion(index) {
  const q = questions[index];
  questionText.textContent = q.text;
  questionCounter.textContent = `Question ${index + 1} of ${questions.length}`;
  answerOptions.innerHTML = "";

  q.options.forEach(option => {
    const btn = document.createElement("button");
    btn.className = "answer-btn";
    btn.textContent = option;
    btn.addEventListener("click", () => selectAnswer(q.id, option, btn));
    answerOptions.appendChild(btn);
  });

  const pct = Math.round(((index) / questions.length) * 40) + 5;
  setProgress(pct, `Step 1 of 3 — Question ${index + 1}/${questions.length}`);
}

function selectAnswer(qId, answer, btn) {
  document.querySelectorAll(".answer-btn").forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  answers[qId] = answer;

  setTimeout(() => {
    currentQuestionIndex++;
    if (currentQuestionIndex < questions.length) {
      showQuestion(currentQuestionIndex);
    } else {
      submitQuestionnaire();
    }
  }, 350);
}

async function submitQuestionnaire() {
  await fetch(`${API_BASE}/questionnaire/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(answers)
  });
  showStep("verification");
  setProgress(50, "Step 2 of 3 — Pill Verification");
}

// --- STEP 2: Pill Verification ---
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 } }
    });
    video.srcObject = stream;
  } catch {
    console.warn("Camera unavailable");
  }
}

captureBtn.addEventListener("click", async () => {
  captureBtn.disabled = true;
  captureBtn.textContent = "Analyzing...";
  verificationResult.style.display = "none";
  confirmBtn.style.display = "none";

  const size = 224;
  captureCanvas.width = size;
  captureCanvas.height = size;
  const ctx = captureCanvas.getContext("2d");

  const vw = video.videoWidth;
  const vh = video.videoHeight;
  const roiSize = Math.floor(Math.min(vw, vh) * 0.55);
  const sx = (vw - roiSize) / 2;
  const sy = (vh - roiSize) / 2;
  ctx.drawImage(video, sx, sy, roiSize, roiSize, 0, 0, size, size);

  captureCanvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append("file", blob, "pill.jpg");

    try {
      const res = await fetch(`${API_BASE}/verify-pill`, { method: "POST", body: formData });
      const data = await res.json();

      verificationResult.style.display = "block";

      if (res.ok && data.status === "match") {
        verificationResult.className = "verification-result success";
        verificationResult.textContent = data.message;
        verifiedPillId = data.predicted_id;
        confirmBtn.style.display = "block";
        setProgress(75, "Step 2 of 3 — Pill Verified ✅");
      } else {
        verificationResult.className = "verification-result error";
        verificationResult.textContent = data.message;
        captureBtn.disabled = false;
        captureBtn.textContent = "📸 Try Again";
      }
    } catch {
      verificationResult.className = "verification-result error";
      verificationResult.textContent = "Connection error. Please ensure the backend is running.";
      captureBtn.disabled = false;
      captureBtn.textContent = "📸 Try Again";
    }
  }, "image/jpeg", 0.85);
});

confirmBtn.addEventListener("click", async () => {
  if (!verifiedPillId) return;
  const formData = new FormData();
  formData.append("pill_id", verifiedPillId);

  await fetch(`${API_BASE}/confirm-ingestion`, { method: "POST", body: formData });
  showStep("complete");
  setProgress(100, "Step 3 of 3 — Complete");
});

// --- Navigation ---
function showStep(name) {
  document.querySelectorAll(".step").forEach(s => s.classList.remove("active"));
  if (name === "questionnaire") stepQuestionnaire.classList.add("active");
  if (name === "verification")  stepVerification.classList.add("active");
  if (name === "complete")      stepComplete.classList.add("active");
}

init();
