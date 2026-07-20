import styles from "./SourceTypeTag.module.css";

export function SourceTypeTag({ kind }: { kind: string }) {
  return <span className={styles.tag}>{kind.toUpperCase()} · NOTION</span>;
}
