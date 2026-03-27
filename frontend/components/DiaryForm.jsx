import { useState } from "react";
import styles from "../styles/DiaryForm.module.css";

export default function DiaryForm({ onContinue }) {
  const [pain, setPain] = useState(4);
  const [fatigue, setFatigue] = useState("");
  const [nausea, setNausea] = useState("");
  const [notes, setNotes] = useState("");

  const valid = fatigue !== "" && nausea !== "";

  return (
    <div className={styles.wrapper}>
      <div className={styles.heroCard}>
        <div className={styles.heroTop}>
          <span className={styles.kicker}>Daily ePRO</span>
          <h2 className={styles.title}>How are you feeling today?</h2>
          <p className={styles.subtitle}>
            Please answer the questions below before taking your study medication.
          </p>
        </div>

        <div className={styles.painCard}>
          <div className={styles.painHeader}>
            <span className={styles.questionTag}>Pain score</span>
            <span className={styles.painValue}>{pain}/10</span>
          </div>

          <p className={styles.questionText}>
            On a scale from 0 to 10, how much pain are you feeling right now?
          </p>

          <input
            type="range"
            min="0"
            max="10"
            value={pain}
            onChange={(e) => setPain(Number(e.target.value))}
            className={styles.slider}
          />

          <div className={styles.scaleRow}>
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                type="button"
                className={`${styles.scaleBtn} ${pain === i ? styles.active : ""}`}
                onClick={() => setPain(i)}
              >
                {i}
              </button>
            ))}
          </div>

          <div className={styles.scaleLabels}>
            <span>No pain</span>
            <span>Worst imaginable</span>
          </div>
        </div>

        <div className={styles.questionCard}>
          <p className={styles.questionText}>How severe is your fatigue today?</p>
          <div className={styles.optionRow}>
            {["None", "Mild", "Moderate", "Severe"].map((opt) => (
              <button
                key={opt}
                type="button"
                className={`${styles.optionBtn} ${fatigue === opt ? styles.active : ""}`}
                onClick={() => setFatigue(opt)}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.questionCard}>
          <p className={styles.questionText}>Have you felt nausea today?</p>
          <div className={styles.optionRow}>
            {["Yes", "No"].map((opt) => (
              <button
                key={opt}
                type="button"
                className={`${styles.optionBtn} ${nausea === opt ? styles.active : ""}`}
                onClick={() => setNausea(opt)}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.questionCard}>
          <label className={styles.questionText}>Optional notes</label>
          <textarea
            className={styles.textarea}
            rows={4}
            placeholder="Anything else you want to record today"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        <div className={styles.ctaCard}>
          <div>
            <h3 className={styles.ctaTitle}>Next step</h3>
            <p className={styles.ctaText}>
              It’s time to take the medication. Please show the pill provided by the investigator.
            </p>
          </div>

          <button
            className={styles.continueBtn}
            disabled={!valid}
            onClick={() =>
              onContinue({
                PAIN_NRS: pain,
                FATIGUE: fatigue,
                NAUSEA: nausea,
                NOTES: notes
              })
            }
          >
            Continue to medication check
          </button>
        </div>
      </div>
    </div>
  );
}