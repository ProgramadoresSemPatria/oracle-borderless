import { Logo } from "../Logo/Logo";
import styles from "./Footer.module.css";

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <span className={styles.left}><Logo size={26} /> Oracle Borderless · oracle.borderless.dev</span>
        <span className={styles.right}>Fonte única da verdade · movido a fontes aprovadas</span>
      </div>
    </footer>
  );
}
