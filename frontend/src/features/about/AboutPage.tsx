import { Header } from "../../components/Header/Header";
import { Footer } from "../../components/Footer/Footer";
import { Button } from "../../components/Button/Button";
import styles from "./AboutPage.module.css";

const CARDS = [
  { icon: "✓", title: "Aprovado no Notion", body: "Cada resposta nasce de um documento que alguém do ecossistema liberou. Fonte única da verdade, de verdade." },
  { icon: "⃠", title: "Zero confidencial", body: "Docs 🔴 Restrito e dados sensíveis ficam de fora do índice. O oráculo não tem como acessá-los." },
  { icon: "↻", title: "Sempre sincronizado", body: "Quando um documento aprovado muda no Notion, o oráculo passa a responder pela versão mais recente." },
];

const FLOW = [
  { label: "ORIGEM", title: "Notion", body: "Documentos aprovados do ecossistema (SOPs, sistemas, vagas)." },
  { label: "FILTRO", title: "Só liberados", body: "Confidenciais e restritos são descartados antes de indexar." },
  { label: "ÍNDICE", title: "Base do oráculo", body: "Conteúdo liberado vira a única fonte consultável." },
  { label: "SAÍDA", title: "Resposta citada", body: "Linguagem clara + cards de fonte com trecho e link." },
];

export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="container">
        <p className="eyebrow">Sobre &amp; Fontes</p>
        <h1 className={styles.title}>De onde vem a<br />verdade do oráculo</h1>
        <p className={styles.intro}>
          O Oracle Borderless não inventa nem opina. Ele lê apenas os documentos que o
          ecossistema liberou no Notion e responde com base neles — citando cada fonte que usou.
          Se algo não está documentado e aprovado, o oráculo diz que não sabe.
        </p>
        <div className={styles.cards}>
          {CARDS.map((c) => (
            <article key={c.title} className={styles.card}>
              <span className={styles.icon}>{c.icon}</span>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </article>
          ))}
        </div>
        <section className={styles.flowPanel}>
          <h2>O fluxo do conhecimento</h2>
          <div className={styles.flowGrid}>
            {FLOW.map((f) => (
              <div key={f.label} className={styles.flowCol}>
                <span className={styles.flowLabel}>{f.label}</span>
                <strong>{f.title}</strong>
                <p>{f.body}</p>
              </div>
            ))}
          </div>
        </section>
        <div className={styles.callout}>
          <span className={styles.calloutCheck}>✓</span>
          <p>Documentos marcados como 🔴 <strong>Restrito</strong> nunca entram no oráculo. Dados operacionais
            (como resultados de alunos) só aparecem quando o documento de origem foi liberado — e sempre com a fonte citada.</p>
        </div>
        <div style={{ margin: "40px 0" }}>
          <Button variant="primary" to="/oracle">Fazer uma pergunta →</Button>
        </div>
      </main>
      <Footer />
    </>
  );
}
