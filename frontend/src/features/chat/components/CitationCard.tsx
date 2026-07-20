import { useState } from "react";
import type { Citation } from "../../../lib/types";
import { safeUrl } from "../../../lib/utils/safeUrl";
import { toPlainText } from "../../../lib/utils/text";
import styles from "../ChatPage.module.css";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [open, setOpen] = useState(false);
  const isWeb = citation.source_type === "web";
  const href = isWeb ? safeUrl(citation.url) : null;
  const label = isWeb ? "Link externo" : "Base de conhecimento";
  const snippet = toPlainText(citation.snippet);
  return (
    <div className={styles.citation}>
      <button className={styles.citationHead} onClick={() => setOpen((o) => !o)}>
        <span className={styles.citationTag}>{label}</span>
        <strong>{citation.title}</strong>
        <span className={styles.citationIndex}>[{index}] ▾</span>
      </button>
      {open && (
        <div className={styles.citationBody}>
          {snippet && <p>{snippet}</p>}
          {href ? (
            <a href={href} target="_blank" rel="noreferrer">Abrir fonte →</a>
          ) : (
            <span className={styles.citationRef}>Referência da base de conhecimento</span>
          )}
        </div>
      )}
    </div>
  );
}
