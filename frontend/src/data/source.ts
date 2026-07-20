import type { AskInput, ConversationDetail, ConversationSummary } from "../lib/types";
import * as api from "../lib/api/conversations";
import { demoStream } from "../lib/demo/demoStream";
import { DEMO_CONVERSATIONS, DEMO_DETAILS } from "../lib/demo/demoData";

const DEMO = import.meta.env.VITE_DEMO_MODE === "true";

export function listConversations(): Promise<ConversationSummary[]> {
  if (DEMO) return Promise.resolve(DEMO_CONVERSATIONS);
  return api.listConversations();
}

export function getConversation(id: string): Promise<ConversationDetail> {
  if (DEMO) {
    return Promise.resolve(
      DEMO_DETAILS[id] ?? { id, title: null, messages: [] }
    );
  }
  return api.getConversation(id);
}

export function askStream(input: AskInput) {
  return DEMO ? demoStream(input) : api.askStream(input);
}

export const isDemo = DEMO;
