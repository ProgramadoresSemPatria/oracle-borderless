import { Badge } from "../../../components/Badge/Badge";
import { Button } from "../../../components/Button/Button";
import { Logo } from "../../../components/Logo/Logo";
import { SourceTypeTag } from "../../../components/SourceTypeTag/SourceTypeTag";
import styles from "../LandingPage.module.css";

export function Hero() {
  return (
    <section className={`container ${styles.hero}`}>
      <div className={styles.heroCopy}>
        <Badge tone="emerald">Fonte única da verdade do ecossistema</Badge>
        <h1 className={styles.headline}>
          Pergunte.<br />Receba a verdade,<br />
          <span className="text-gradient">com as fontes.</span>
        </h1>
        <p className={styles.sub}>
          O Oracle Borderless é um oráculo de IA que responde qualquer pergunta sobre as
          regras e a operação do ecossistema — em linguagem clara e sempre baseado{" "}
          <strong>exclusivamente em documentos aprovados</strong>. Cada resposta cita de onde veio.
        </p>
        <div className={styles.heroCtas}>
          <Button variant="gradient" to="/oracle">Abrir o oráculo →</Button>
          <Button variant="ghost" to="/about">Ver as fontes</Button>
        </div>
      </div>
      <aside className={styles.previewCard}>
        <header className={styles.previewHead}>
          <Logo size={30} /> <strong>Oráculo</strong>
          <span className={styles.online}>● online</span>
        </header>
        <div className={styles.previewUser}>Qual a nomenclatura de campanhas no Meta Ads?</div>
        <div className={styles.previewBot}>
          A nomenclatura oficial está no <strong>SOP-GM-06</strong> e usa uma estrutura de
          3 níveis: campanha, conjunto e anúncio.
        </div>
        <div className={styles.previewSource}>
          <SourceTypeTag kind="SOP" /> <strong>SOP-GM-06 — Nomenclatura de Campanhas</strong>
        </div>
      </aside>
    </section>
  );
}
