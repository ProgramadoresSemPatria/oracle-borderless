import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import styles from "./Button.module.css";

type Props = {
  variant?: "primary" | "ghost" | "gradient";
  to?: string;
  onClick?: () => void;
  children: ReactNode;
};

export function Button({ variant = "primary", to, onClick, children }: Props) {
  const cls = `${styles.btn} ${styles[variant]}`;
  if (to) return <Link className={cls} to={to}>{children}</Link>;
  return <button className={cls} onClick={onClick}>{children}</button>;
}
