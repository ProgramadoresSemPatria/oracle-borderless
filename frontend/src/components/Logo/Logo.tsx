import styles from "./Logo.module.css";

// Auto-detect: if an official logo.png is dropped in src/assets/, use it; else the svg fallback.
const assets = import.meta.glob("../../assets/logo.{png,svg}", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

const pngKey = Object.keys(assets).find((k) => k.endsWith(".png"));
const svgKey = Object.keys(assets).find((k) => k.endsWith(".svg"));
const logoUrl = (pngKey && assets[pngKey]) || (svgKey && assets[svgKey]) || "";

export function Logo({ size = 36 }: { size?: number }) {
  return (
    <span className={styles.chip} style={{ width: size, height: size }}>
      <img src={logoUrl} alt="Oracle Borderless" />
    </span>
  );
}
