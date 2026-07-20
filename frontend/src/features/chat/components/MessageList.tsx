import type { Citation } from "../../../lib/types";
import { MessageBubble } from "./MessageBubble";

export type Turn = { id: string; role: "user" | "assistant"; content: string; citations?: Citation[] };

export function MessageList({ turns, streamingIndex }: { turns: Turn[]; streamingIndex: number | null }) {
  return (
    <>
      {turns.map((t, i) => (
        <MessageBubble
          key={t.id}
          role={t.role}
          content={t.content}
          citations={t.citations}
          streaming={streamingIndex === i}
        />
      ))}
    </>
  );
}
