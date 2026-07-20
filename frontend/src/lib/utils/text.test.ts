import { describe, expect, it } from "vitest";
import { stripHtml, toPlainText } from "./text";

describe("stripHtml", () => {
  it("removes HTML tags", () => {
    expect(stripHtml("<details><summary>x</summary>y</details>")).toBe("xy");
  });

  it("preserves math comparisons (does not treat < > as tags)", () => {
    expect(stripHtml("score < 60 e resultado > 0")).toBe("score < 60 e resultado > 0");
  });

  it("still removes real HTML tags including attributes", () => {
    expect(stripHtml('<a href="http://x">link</a>')).toBe("link");
    expect(stripHtml("<details><summary>x</summary>y</details>")).toBe("xy");
  });

  it("keeps comparisons intact through toPlainText", () => {
    const out = toPlainText("Se score < 60 então reprova; caso > 90, destaque.");
    expect(out).toContain("< 60");
    expect(out).toContain("> 90");
  });
});

describe("toPlainText", () => {
  it("strips markdown markup while keeping the words", () => {
    const result = toPlainText(
      "## Título\n\n**negrito** e *itálico*\n- item 1\n- item 2\n[link](http://x)"
    );
    expect(result).not.toMatch(/#/);
    expect(result).not.toMatch(/\*/);
    expect(result).not.toMatch(/^\s*-\s/m);
    expect(result).not.toMatch(/[[\]]/);
    expect(result).not.toMatch(/\(http/);
    expect(result).toContain("Título");
    expect(result).toContain("negrito");
    expect(result).toContain("item 1");
    expect(result).toContain("link");
  });

  it("strips stray HTML alongside markdown", () => {
    const result = toPlainText(
      "</details> <details> <summary>PSP x BASE</summary> A Base..."
    );
    expect(result).not.toMatch(/[<>]/);
    expect(result).toContain("PSP x BASE");
  });
});
