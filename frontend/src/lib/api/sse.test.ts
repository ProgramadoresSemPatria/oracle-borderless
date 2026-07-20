import { describe, it, expect } from "vitest";
import { parseSSE } from "./sse";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const out: { event: string; data: string }[] = [];
  for await (const evt of parseSSE(stream)) out.push(evt);
  return out;
}

describe("parseSSE", () => {
  it("parses complete events", async () => {
    const events = await collect(
      streamOf([
        "event: conversation\ndata: {\"id\":\"abc\"}\n\n",
        "event: token\ndata: {\"text\":\"oi\"}\n\n",
      ])
    );
    expect(events).toEqual([
      { event: "conversation", data: '{"id":"abc"}' },
      { event: "token", data: '{"text":"oi"}' },
    ]);
  });

  it("reassembles an event split across chunks", async () => {
    const events = await collect(streamOf(["event: token\nda", 'ta: {"text":"x"}\n\n']));
    expect(events).toEqual([{ event: "token", data: '{"text":"x"}' }]);
  });

  it("ignores a trailing partial event with no terminator", async () => {
    const events = await collect(streamOf(["event: token\ndata: {}"]));
    expect(events).toEqual([]);
  });

  it("joins multiple data: lines within one event", async () => {
    const events = await collect(streamOf(["event: token\ndata: line1\ndata: line2\n\n"]));
    expect(events).toEqual([{ event: "token", data: "line1\nline2" }]);
  });
});
