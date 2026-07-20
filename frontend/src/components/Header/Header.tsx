import { Link } from "react-router-dom";
import { Logo } from "../Logo/Logo";
import { Button } from "../Button/Button";
import styles from "./Header.module.css";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>
        <Link to="/" className={styles.brand}>
          <Logo size={40} />
          <span>Oracle <span className="text-gradient">Borderless</span></span>
        </Link>
        <nav className={styles.nav}>
          <Link to="/about">Sobre &amp; Fontes</Link>
          <Link to="/knowledge">Base de conhecimento</Link>
          <Button variant="gradient" to="/oracle">Abrir o oráculo →</Button>
        </nav>
      </div>
    </header>
  );
}
