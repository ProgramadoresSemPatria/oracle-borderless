import { Logo } from "../../../components/Logo/Logo";
import styles from "../ChatPage.module.css";

const EXAMPLES = [
  { tag: "GROWTH", text: "Qual a nomenclatura de campanhas no Meta Ads?" },
  { tag: "CULTURA", text: "Como funciona a Review Mensal (1:1)?" },
  { tag: "OPERAÇÃO", text: "Como é o upload semanal de vídeo no YouTube?" },
  { tag: "DEMO", text: "Ver o estado de erro (falha ao gerar)", value: "[demo-error]" },
];

export function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className={styles.empty}>
      <Logo size={72} />
      <h2>Olá! Pergunte qualquer coisa.</h2>
      <p>Eu respondo sobre as regras e a operação do ecossistema — sempre com base nos documentos aprovados, e sempre citando as fontes.</p>
      <div className={styles.exampleGrid}>
        {EXAMPLES.map((e) => (
          <button key={e.tag} className={styles.exampleCard} onClick={() => onPick(e.value ?? e.text)}>
            <span className={styles.exampleTag}>{e.tag}</span>
            <span>{e.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
