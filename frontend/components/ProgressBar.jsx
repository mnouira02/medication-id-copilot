import styles from '../styles/ProgressBar.module.css';

export default function ProgressBar({ progress, label }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${progress}%` }} />
      </div>
      <p className={styles.label}>{label}</p>
    </div>
  );
}
