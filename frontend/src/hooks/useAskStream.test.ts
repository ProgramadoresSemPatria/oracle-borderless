import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { AskEvent } from "../lib/types";

const scenario = vi.hoisted(() => ({ events: [] as AskEvent[] }));
// Gate for the superseded-run test: the first ask()'s generator awaits this
// promise before yielding its later (stale) events, so we can start the
// second ask() while the first is still "in flight" and only then let the
// first run's remaining events attempt to land.
const gate = vi.hoisted(() => ({
  promise: Promise.resolve() as Promise<void>,
  resolve: (() => {}) as () => void,
}));

vi.mock("../data/source", () => ({
  isDemo: true,
  askStream: async function* (input: { question: string }) {
    if (input.question === "first (gated)") {
      yield { type: "conversation", id: "stale-convo" } as AskEvent;
      yield { type: "token", text: "STALE_TOKEN " } as AskEvent;
      await gate.promise;
      yield { type: "token", text: "should-not-appear" } as AskEvent;
      yield { type: "done" } as AskEvent;
      return;
    }
    for (const e of scenario.events) yield e;
  },
}));

import { useAskStream } from "./useAskStream";

beforeEach(() => {
  scenario.events = [];
});

describe("useAskStream", () => {
  it("moves through thinking → streaming → done and accumulates tokens + citations", async () => {
    scenario.events = [
      { type: "conversation", id: "c9" },
      { type: "token", text: "olá " },
      { type: "token", text: "mundo" },
      { type: "sources", citations: [{ source_type: "SOP", title: "T", url: "https://x", snippet: "s" }] },
      { type: "done" },
    ];
    const { result } = renderHook(() => useAskStream());
    await act(async () => {
      await result.current.ask({ question: "oi" });
    });
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.answer).toBe("olá mundo");
    expect(result.current.conversationId).toBe("c9");
    expect(result.current.citations).toHaveLength(1);
  });

  it("enters error status on an error event", async () => {
    scenario.events = [
      { type: "conversation", id: "c9" },
      { type: "error", message: "falhou" },
      { type: "done" },
    ];
    const { result } = renderHook(() => useAskStream());
    await act(async () => {
      await result.current.ask({ question: "[demo-error]" });
    });
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("falhou");
  });

  it("a second ask() supersedes a first still-running one; the stale run's later events are dropped", async () => {
    gate.promise = new Promise<void>((resolve) => {
      gate.resolve = resolve;
    });
    scenario.events = [
      { type: "conversation", id: "c-second" },
      { type: "token", text: "second answer" },
      { type: "done" },
    ];
    const { result } = renderHook(() => useAskStream());

    let firstRunPromise!: Promise<void>;
    await act(async () => {
      // Not awaited: this run gates before its final events, staying
      // "in flight" while we start (and finish) a second, superseding run.
      firstRunPromise = result.current.ask({ question: "first (gated)" });
      await Promise.resolve();
      await Promise.resolve();
    });

    // The first run's pre-gate events landed normally (no supersession yet).
    expect(result.current.conversationId).toBe("stale-convo");
    expect(result.current.answer).toBe("STALE_TOKEN ");

    await act(async () => {
      await result.current.ask({ question: "second" });
    });

    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.answer).toBe("second answer");
    expect(result.current.conversationId).toBe("c-second");

    // Release the stale run's remaining events now that it has been
    // superseded; they must be dropped rather than clobbering state.
    await act(async () => {
      gate.resolve();
      await firstRunPromise;
    });

    expect(result.current.status).toBe("done");
    expect(result.current.answer).toBe("second answer");
    expect(result.current.conversationId).toBe("c-second");
  });
});
