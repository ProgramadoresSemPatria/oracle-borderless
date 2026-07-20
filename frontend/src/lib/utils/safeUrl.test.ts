import { describe, it, expect } from "vitest";
import { safeUrl } from "./safeUrl";

describe("safeUrl", () => {
  it("accepts http and https", () => {
    expect(safeUrl("https://notion.so/x")).toBe("https://notion.so/x");
    expect(safeUrl("http://notion.so/x")).toBe("http://notion.so/x");
  });
  it("rejects other schemes and garbage", () => {
    expect(safeUrl("javascript:alert(1)")).toBeNull();
    expect(safeUrl("not a url")).toBeNull();
    expect(safeUrl("")).toBeNull();
  });
});
