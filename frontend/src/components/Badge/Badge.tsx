import type { ReactNode } from "react";
import styles from "./Badge.module.css";

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "emerald"; children: ReactNode }) {
  return (
    <span className={`${styles.badge} ${styles[tone]}`}>
      <span className={styles.dot} />
      {children}
    </span>
  );
}
