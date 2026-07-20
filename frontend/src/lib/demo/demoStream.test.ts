import { describe, it, expect } from "vitest";
import { demoStream } from "./demoStream";
import type { AskEvent } from "../types";

async function collect(input: { question: string; conversationId?: string }) {
  const events: AskEvent[] = [];
  for await (const e of demoStream(input)) events.push(e);
  return events;
}

describe("demoStream", () => {
  it("emits conversation, tokens, sources, done on success", async () => {
    const events = await collect({ question: "qual a nomenclatura?" });
    expect(events[0].type).toBe("conversation");
    expect(events.some((e) => e.type === "token")).toBe(true);
    expect(events.some((e) => e.type === "sources")).toBe(true);
    expect(events.at(-1)?.type).toBe("done");
  });

  it("emits an error path for the [demo-error] sentinel", async () => {
    const events = await collect({ question: "[demo-error]" });
    expect(events.some((e) => e.type === "error")).toBe(true);
    expect(events.some((e) => e.type === "token")).toBe(false);
    expect(events.at(-1)?.type).toBe("done");
  });
});
