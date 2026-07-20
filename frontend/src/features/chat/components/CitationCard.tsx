import { useState } from "react";
import type { Citation } from "../../../lib/types";
import { SourceTypeTag } from "../../../components/SourceTypeTag/SourceTypeTag";
import { safeUrl } from "../../../lib/utils/safeUrl";
import styles from "../ChatPage.module.css";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [open, setOpen] = useState(false);
  const href = safeUrl(citation.url);
  return (
    <div className={styles.citation}>
      <button className={styles.citationHead} onClick={() => setOpen((o) => !o)}>
        <SourceTypeTag kind={citation.source_type} />
        <strong>{citation.title}</strong>
        <span className={styles.citationIndex}>[{index}] ▾</span>
      </button>
      {open && (
        <div className={styles.citationBody}>
          <p>{citation.snippet}</p>
          {href && <a href={href} target="_blank" rel="noreferrer">Abrir no Notion →</a>}
        </div>
      )}
    </div>
  );
}
