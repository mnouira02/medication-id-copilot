const API_BASE = "http://localhost:8000";

const video = document.getElementById("video");
const captureCanvas = document.getElementById("capture-canvas");
const captureBtn = document.getElementById("capture-btn");
const captureSection = document.getElementById("capture-section");
const chatSection = document.getElementById("chat-section");
const chatLog = document.getElementById("chat-log");
const imprintInput = document.getElementById("imprint-input");
const imprintField = document.getElementById("imprint-field");
const submitImprint = document.getElementById("submit-imprint");

let extractedFeatures = {};

// --- Phase 1: Start Camera ---
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 } }
    });
    video.srcObject = stream;
  } catch (err) {
    addCopilotMessage("Camera access is required for pill identification. Please allow camera permissions.");
  }
}

// --- Phase 1: Crop ROI (224x224) and send to backend ---
captureBtn.addEventListener("click", async () => {
  const size = 224;
  captureCanvas.width = size;
  captureCanvas.height = size;
  const ctx = captureCanvas.getContext("2d");

  // Crop center region matching the ROI overlay (55% of video)
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  const roiSize = Math.floor(Math.min(vw, vh) * 0.55);
  const sx = (vw - roiSize) / 2;
  const sy = (vh - roiSize) / 2;

  ctx.drawImage(video, sx, sy, roiSize, roiSize, 0, 0, size, size);

  captureCanvas.toBlob(async (blob) => {
    captureSection.style.display = "none";
    chatSection.style.display = "flex";
    chatSection.style.flexDirection = "column";
    addCopilotMessage("📸 Got it! Analyzing the pill...");
    await sendImageToBackend(blob);
  }, "image/jpeg", 0.85);
});

async function sendImageToBackend(blob) {
  const formData = new FormData();
  formData.append("file", blob, "pill.jpg");

  try {
    const res = await fetch(`${API_BASE}/analyze-image`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    extractedFeatures = data.extracted_features || {};
    addCopilotMessage(data.copilot_message);

    // Show imprint input for Phase 3 HITL
    imprintInput.style.display = "flex";
    imprintField.focus();
  } catch (err) {
    addCopilotMessage("Connection error. Please ensure the backend server is running.");
  }
}

// --- Phase 3: Submit imprint ---
submitImprint.addEventListener("click", async () => {
  const imprint = imprintField.value.trim().toUpperCase();
  if (!imprint) return;

  addUserMessage(imprint);
  imprintInput.style.display = "none";
  addCopilotMessage("🔍 Looking up in the NIH RxImage database...");

  const formData = new FormData();
  formData.append("color", extractedFeatures.color || "unknown");
  formData.append("shape", extractedFeatures.shape || "unknown");
  formData.append("imprint", imprint);

  try {
    const res = await fetch(`${API_BASE}/identify`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    addCopilotMessage(data.copilot_message);

    if (data.status === "identified" && data.raw_data?.imageUrl) {
      addImageMessage(data.raw_data.imageUrl, data.raw_data.name);
    }
  } catch (err) {
    addCopilotMessage("Failed to reach the identification service. Please try again.");
  }
});

imprintField.addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitImprint.click();
});

// --- UI Helpers ---
function addCopilotMessage(text) {
  const div = document.createElement("div");
  div.className = "msg copilot";
  div.innerHTML = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addUserMessage(text) {
  const div = document.createElement("div");
  div.className = "msg user";
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addImageMessage(url, name) {
  const img = document.createElement("img");
  img.src = url;
  img.alt = name;
  img.style.cssText = "max-width:120px;border-radius:8px;margin-top:0.5rem;";
  chatLog.appendChild(img);
  chatLog.scrollTop = chatLog.scrollHeight;
}

// Start
startCamera();
