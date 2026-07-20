import { useCallback, useState } from "react";
import type { AskInput, Citation } from "../lib/types";
import { askStream } from "../data/source";

export type AskStatus = "idle" | "thinking" | "streaming" | "done" | "error";

export function useAskStream() {
  const [status, setStatus] = useState<AskStatus>("idle");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const reset = useCallback(() => {
    setStatus("idle");
    setAnswer("");
    setCitations([]);
    setErrorMessage(null);
  }, []);

  const ask = useCallback(async (input: AskInput) => {
    setStatus("thinking");
    setAnswer("");
    setCitations([]);
    setErrorMessage(null);
    try {
      for await (const evt of askStream(input)) {
        if (evt.type === "conversation") setConversationId(evt.id);
        else if (evt.type === "token") {
          setStatus("streaming");
          setAnswer((prev) => prev + evt.text);
        } else if (evt.type === "sources") setCitations(evt.citations);
        else if (evt.type === "error") {
          setErrorMessage(evt.message);
          setStatus("error");
        } else if (evt.type === "done") {
          setStatus((s) => (s === "error" ? "error" : "done"));
        }
      }
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "erro inesperado");
      setStatus("error");
    }
  }, []);

  return { status, answer, citations, conversationId, errorMessage, ask, reset };
}
