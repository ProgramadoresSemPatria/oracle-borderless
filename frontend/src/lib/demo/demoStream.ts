import type { AskEvent, AskInput } from "../types";
import { DEMO_ANSWER, DEMO_ANSWER_CITATIONS } from "./demoData";

const ERROR_SENTINEL = "[demo-error]";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function* demoStream(input: AskInput): AsyncGenerator<AskEvent> {
  const conversationId = input.conversationId ?? "demo-new";
  yield { type: "conversation", id: conversationId };

  if (input.question.includes(ERROR_SENTINEL)) {
    await delay(400);
    yield { type: "error", message: "Não consegui gerar a resposta agora. Tente novamente." };
    yield { type: "done" };
    return;
  }

  await delay(500); // "thinking" window before first token
  for (const word of DEMO_ANSWER.split(" ")) {
    yield { type: "token", text: word + " " };
    await delay(40);
  }
  yield { type: "sources", citations: DEMO_ANSWER_CITATIONS };
  yield { type: "done" };
}
