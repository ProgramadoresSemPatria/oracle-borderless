import type { Citation } from "../../../lib/types";
import { Logo } from "../../../components/Logo/Logo";
import { CitationsBlock } from "./CitationsBlock";
import styles from "../ChatPage.module.css";

type Props = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
};

export function MessageBubble({ role, content, citations, streaming }: Props) {
  if (role === "user") {
    return <div className={styles.userTurn}><div className={styles.userBubble}>{content}</div></div>;
  }
  return (
    <div className={styles.botTurn}>
      <Logo size={34} />
      <div className={styles.botBody}>
        <div className={styles.botText}>
          {content}
          {streaming && <span className={styles.cursor} />}
        </div>
        {citations && <CitationsBlock citations={citations} />}
      </div>
    </div>
  );
}
