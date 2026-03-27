import { useState } from 'react';
import styles from '../styles/DiaryForm.module.css';

const QUESTIONS = [
  { id: 'SMAQ1', text: 'Do you ever forget to take your medicine?', options: ['Yes', 'No'] },
  { id: 'SMAQ2', text: 'Are you careless at times about taking your medicine?', options: ['Yes', 'No'] },
  { id: 'SMAQ3', text: 'When you feel better, do you sometimes stop taking your medicine?', options: ['Yes', 'No'] },
  { id: 'SMAQ4', text: 'If you feel worse when taking the medicine, do you stop?', options: ['Yes', 'No'] },
  { id: 'SMAQ5', text: 'In the past week, how many days did you not take your medicine?',
    options: ['0', '1', '2', '3', '4', '5', '6', '7'] },
  { id: 'SMAQ6', text: 'Have you taken less than 90% of your prescribed doses since your last visit?',
    options: ['Yes', 'No'] },
];

export default function DiaryForm({ subjectId, onSubmitted }) {
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const allAnswered = QUESTIONS.every(q => answers[q.id] !== undefined);

  async function handleSubmit() {
    if (!allAnswered) return;
    setSubmitting(true);
    await fetch('/api/log-adherence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject_id: subjectId,
        event: 'diary_submitted',
        domain: 'QS',
        responses: answers,
        timestamp: new Date().toISOString()
      })
    });
    onSubmitted();
  }

  return (
    <div className={styles.diary}>
      <h2 className={styles.title}>📋 Daily Symptom Diary</h2>
      <p className={styles.subtitle}>Please answer all questions honestly.</p>

      {QUESTIONS.map(q => (
        <div key={q.id} className={styles.questionCard}>
          <p className={styles.questionText}>{q.text}</p>
          <div className={styles.options}>
            {q.options.map(opt => (
              <button
                key={opt}
                className={`${styles.optionBtn} ${answers[q.id] === opt ? styles.selected : ''}`}
                onClick={() => setAnswers(prev => ({ ...prev, [q.id]: opt }))}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      ))}

      <button
        className={styles.submitBtn}
        disabled={!allAnswered || submitting}
        onClick={handleSubmit}
      >
        {submitting ? 'Submitting...' : 'Submit Daily Diary'}
      </button>
    </div>
  );
}
