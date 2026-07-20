export interface Citation {
  source_type: string;
  title: string;
  url: string;
  snippet: string;
  page_id?: string | null;
}

export type MessageRole = "user" | "assistant";

export interface Message {
  role: MessageRole;
  content: string;
  sources?: Citation[];
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  updatedAt: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  messages: Message[];
}

export interface AskInput {
  question: string;
  conversationId?: string;
}

export type AskEvent =
  | { type: "conversation"; id: string }
  | { type: "token"; text: string }
  | { type: "sources"; citations: Citation[] }
  | { type: "error"; message: string }
  | { type: "done" };
