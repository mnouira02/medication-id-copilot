import { useState } from 'react';
import PillGate from '../components/PillGate';
import DiaryForm from '../components/DiaryForm';
import ProgressBar from '../components/ProgressBar';
import styles from '../styles/Home.module.css';

const SUBJECT_ID = 'SUBJ-042'; // In production: from auth token / QR code

export default function Home() {
  const [gateStatus, setGateStatus] = useState('locked'); // locked | verifying | unlocked
  const [diarySubmitted, setDiarySubmitted] = useState(false);

  const progress = diarySubmitted ? 100 : gateStatus === 'unlocked' ? 66 : 10;
  const stepLabel = diarySubmitted
    ? 'Complete ✔️'
    : gateStatus === 'unlocked'
    ? 'Step 2 of 2 — Daily Diary'
    : 'Step 1 of 2 — Medication Verification';

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <span className={styles.trialBadge}>TRIAL-001 · Day {new Date().getDate()}</span>
        <h1>💊 Daily Compliance Check</h1>
        <ProgressBar progress={progress} label={stepLabel} />
      </header>

      {!diarySubmitted && (
        <>
          {gateStatus !== 'unlocked' && (
            <PillGate
              subjectId={SUBJECT_ID}
              onVerified={() => setGateStatus('unlocked')}
            />
          )}

          {gateStatus === 'unlocked' && (
            <DiaryForm
              subjectId={SUBJECT_ID}
              onSubmitted={() => setDiarySubmitted(true)}
            />
          )}
        </>
      )}

      {diarySubmitted && (
        <div className={styles.completeCard}>
          <div className={styles.completeIcon}>✅</div>
          <h2>Visit Complete</h2>
          <p>Your medication intake and diary have been recorded. Thank you.</p>
          <span className={styles.sdtmBadge}>SDTM EX + QS logged</span>
        </div>
      )}

      <footer className={styles.footer}>
        ⚠️ Research prototype. Not a certified medical device.
      </footer>
    </main>
  );
}
