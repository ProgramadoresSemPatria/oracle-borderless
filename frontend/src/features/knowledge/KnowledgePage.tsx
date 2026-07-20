import { useEffect, useState } from "react";
import { Header } from "../../components/Header/Header";
import { Footer } from "../../components/Footer/Footer";
import { Badge } from "../../components/Badge/Badge";
import { SourceTypeTag } from "../../components/SourceTypeTag/SourceTypeTag";
import { listDocuments } from "../../data/documents";
import type { KnowledgeDoc } from "../../lib/demo/demoData";
import styles from "./KnowledgePage.module.css";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  useEffect(() => {
    void listDocuments().then(setDocs);
  }, []);

  return (
    <>
      <Header />
      <main className="container">
        <p className="eyebrow">Base de conhecimento</p>
        <h1 className={styles.title}>Documentos que alimentam o oráculo</h1>
        <div style={{ margin: "16px 0" }}><Badge tone="emerald">Sincronizado com o Notion</Badge></div>
        <p className={styles.note}>
          Somente leitura. Lista dos documentos aprovados atualmente indexados. É daqui
          — e só daqui — que o oráculo tira as respostas.
        </p>
        <table className={styles.table}>
          <thead>
            <tr><th>Documento</th><th>Sincronização</th><th>Status</th></tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>
                  <div className={styles.docCell}>
                    <SourceTypeTag kind={d.kind} />
                    <div>
                      <strong>{d.title}</strong>
                      <span className={styles.origin}>{d.origin}{d.version ? ` · ${d.version}` : " · —"}</span>
                    </div>
                  </div>
                </td>
                <td className={styles.mono}>{d.syncedAt}</td>
                <td>
                  <span className={d.status === "active" ? styles.active : styles.syncing}>
                    ● {d.status === "active" ? "Ativo" : "Sincronizando"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className={styles.footnote}>
          🔒 Documentos 🔴 <strong>Restrito</strong> e materiais confidenciais não são indexados e nunca chegam ao oráculo.
        </div>
      </main>
      <Footer />
    </>
  );
}
