import type { Citation } from "../../../lib/types";
import { CitationCard } from "./CitationCard";
import styles from "../ChatPage.module.css";

export function CitationsBlock({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className={styles.citations}>
      <div className={styles.citationsLabel}>◆ {citations.length} fontes citadas</div>
      {citations.map((c, i) => (
        <CitationCard key={`${c.title}-${i}`} citation={c} index={i + 1} />
      ))}
    </div>
  );
}
