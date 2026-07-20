import { useCallback, useEffect, useState } from "react";
import type { ConversationSummary } from "../lib/types";
import { listConversations } from "../data/source";

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setConversations(await listConversations());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { conversations, refresh, loading };
}
