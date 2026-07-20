import { useEffect, useState } from "react";
import type { ConversationDetail } from "../lib/types";
import { getConversation } from "../data/source";

export function useConversation(id: string | undefined) {
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!id) {
      setDetail(null);
      return;
    }
    let active = true;
    setLoading(true);
    getConversation(id)
      .then((d) => {
        if (active) setDetail(d);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  return { detail, loading };
}
