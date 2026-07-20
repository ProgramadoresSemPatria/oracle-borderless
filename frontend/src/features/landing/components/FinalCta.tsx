import { Button } from "../../../components/Button/Button";
import { Logo } from "../../../components/Logo/Logo";
import styles from "../LandingPage.module.css";

export function FinalCta() {
  return (
    <section className={`container ${styles.section}`}>
      <div className={styles.ctaCard}>
        <Logo size={64} />
        <h2>Pergunte qualquer coisa. Receba a verdade, com as fontes.</h2>
        <p>Sem confidencial, sem achismo. Só o que já está aprovado no ecossistema.</p>
        <Button variant="gradient" to="/oracle">Abrir o oráculo →</Button>
      </div>
    </section>
  );
}
