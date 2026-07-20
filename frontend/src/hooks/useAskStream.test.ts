import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { AskEvent } from "../lib/types";

const scenario = vi.hoisted(() => ({ events: [] as AskEvent[] }));

vi.mock("../data/source", () => ({
  isDemo: true,
  askStream: async function* () {
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
});
