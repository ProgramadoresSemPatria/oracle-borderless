import { describe, expect, it } from "vitest";
import { stripHtml, toPlainText } from "./text";

describe("stripHtml", () => {
  it("removes HTML tags", () => {
    expect(stripHtml("<details><summary>x</summary>y</details>")).toBe("xy");
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
