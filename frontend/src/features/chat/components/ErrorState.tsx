import styles from "../ChatPage.module.css";

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className={styles.errorBox}>
      <p>{message}</p>
      <button className={styles.retry} onClick={onRetry}>Tentar novamente</button>
    </div>
  );
}
