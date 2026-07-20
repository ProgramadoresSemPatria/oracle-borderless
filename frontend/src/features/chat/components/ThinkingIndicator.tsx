import { Logo } from "../../../components/Logo/Logo";
import styles from "../ChatPage.module.css";

export function ThinkingIndicator() {
  return (
    <div className={styles.botTurn}>
      <Logo size={34} />
      <div className={styles.thinking}><span /><span /><span /></div>
    </div>
  );
}
