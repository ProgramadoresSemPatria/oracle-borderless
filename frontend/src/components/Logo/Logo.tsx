import logoUrl from "../../assets/logo.svg";
import styles from "./Logo.module.css";

export function Logo({ size = 36 }: { size?: number }) {
  return (
    <span className={styles.chip} style={{ width: size, height: size }}>
      <img src={logoUrl} alt="Oracle Borderless" />
    </span>
  );
}
