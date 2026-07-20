import { Link } from "react-router-dom";
import { Logo } from "../../../components/Logo/Logo";
import type { ConversationSummary } from "../../../lib/types";
import styles from "../ChatPage.module.css";

type Props = {
  conversations: ConversationSummary[];
  activeId: string | null;
  onNew: () => void;
  onOpen: (id: string) => void;
  userEmail: string;
};

export function Sidebar({ conversations, activeId, onNew, onOpen, userEmail }: Props) {
  return (
    <aside className={styles.sidebar}>
      <Link to="/" className={styles.sidebarBrand}><Logo size={34} /> Oracle Borderless</Link>
      <button className={styles.newBtn} onClick={onNew}>+ Nova conversa</button>
      <div className={styles.listLabel}>Conversas</div>
      <ul className={styles.convList}>
        {conversations.map((c) => (
          <li key={c.id}>
            <button
              className={c.id === activeId ? styles.convActive : styles.convItem}
              onClick={() => onOpen(c.id)}
            >
              <strong>{c.title ?? "(sem título)"}</strong>
            </button>
          </li>
        ))}
      </ul>
      <div className={styles.sidebarFoot}>
        <Link to="/about">Sobre &amp; Fontes</Link>
        <Link to="/knowledge">Base de conhecimento</Link>
        <div className={styles.userChip}>
          <span className={styles.avatar}>{userEmail[0]?.toUpperCase()}</span>
          <div><strong>{userEmail}</strong><span>autenticado na borda</span></div>
        </div>
      </div>
    </aside>
  );
}
