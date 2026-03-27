import { useState } from "react";
import DiaryForm from "../components/DiaryForm";
import PillGate from "../components/PillGate";
import ProgressBar from "../components/ProgressBar";
import styles from "../styles/Home.module.css";

const SUBJECT_ID = "SUBJ-042";
const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:3001";

export default function Home() {
  const [step, setStep] = useState("diary"); // diary | verify | complete
  const [diaryData, setDiaryData] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const progress = step === "diary" ? 35 : step === "verify" ? 72 : 100;
  const label =
    step === "diary"
      ? "Step 1 of 2 — Daily ePRO"
      : step === "verify"
        ? "Step 2 of 2 — Medication Verification"
        : "Complete";

  async function handleDiaryContinue(payload) {
    setDiaryData(payload);
    setStep("verify");
  }

  async function handleVerified(meta) {
    setSubmitting(true);

    try {
      await fetch(`${API_BASE}/api/log-adherence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_id: SUBJECT_ID,
          event: "diary_submitted",
          domain: "QS",
          responses: diaryData,
          timestamp: new Date().toISOString()
        })
      });

      await fetch(`${API_BASE}/api/log-adherence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_id: SUBJECT_ID,
          event: "dose_verified",
          dose_verified: true,
          confidence: meta.confidence,
          predicted_class: meta.predictedClass,
          timestamp: new Date().toISOString()
        })
      });

      setStep("complete");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <span className={styles.trialBadge}>TRIAL-001 · Daily Visit</span>
        <h1>Edge AI-Gated ePRO</h1>
        <p className={styles.subtitle}>
          Complete your diary, then verify the study medication.
        </p>
        <ProgressBar progress={progress} label={label} />
      </header>

      {step === "diary" && (
        <DiaryForm onContinue={handleDiaryContinue} />
      )}

      {step === "verify" && (
        <PillGate
          subjectId={SUBJECT_ID}
          onVerified={handleVerified}
          disabled={submitting}
        />
      )}

      {step === "complete" && (
        <div className={styles.completeCard}>
          <div className={styles.completeIcon}>✅</div>
          <h2>Visit Complete</h2>
          <p>
            Your diary and medication verification have been recorded successfully.
          </p>
          <span className={styles.sdtmBadge}>Telemetry logged</span>
        </div>
      )}

      <footer className={styles.footer}>
        Research prototype. No image or video leaves the device during inference.
      </footer>
    </main>
  );
}