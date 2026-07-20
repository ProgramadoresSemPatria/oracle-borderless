import styles from "../LandingPage.module.css";

const ITEMS = [
  { icon: "✓", title: "Só fontes liberadas", body: "A base vem exclusivamente de documentos aprovados. O que não foi liberado simplesmente não existe para o oráculo." },
  { icon: "⃠", title: "Nada confidencial", body: "Materiais restritos nunca são indexados. Se a informação é sensível, o oráculo não a acessa nem revela." },
  { icon: "◎", title: "Sempre com citação", body: "Toda resposta mostra de onde veio — título, tipo, trecho e link. Confiança verificável, não fé cega." },
];

export function Differentiators() {
  return (
    <section className={`container ${styles.section}`}>
      <div className={styles.grid3}>
        {ITEMS.map((it) => (
          <article key={it.title} className={styles.diffCard}>
            <span className={styles.diffIcon}>{it.icon}</span>
            <h3>{it.title}</h3>
            <p>{it.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
