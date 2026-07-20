import styles from "../LandingPage.module.css";

const STEPS = [
  { n: "01", title: "Você pergunta", body: "Em linguagem natural, do jeito que falaria com um colega. Sem sintaxe, sem menu." },
  { n: "02", title: "Busca em fontes aprovadas", body: "O oráculo procura apenas nos documentos liberados do Notion — nada confidencial entra na busca." },
  { n: "03", title: "Resposta citada", body: "Você recebe uma resposta clara e cada afirmação vem com o card da fonte que a sustenta." },
];

export function HowItWorks() {
  return (
    <section className={`container ${styles.section}`}>
      <p className="eyebrow" style={{ textAlign: "center" }}>Como funciona</p>
      <h2 className={styles.sectionTitle}>Da pergunta à verdade, em três passos</h2>
      <div className={styles.grid3}>
        {STEPS.map((s) => (
          <article key={s.n} className={styles.stepCard}>
            <span className={styles.stepNum}>{s.n}</span>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
