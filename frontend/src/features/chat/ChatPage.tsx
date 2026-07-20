import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useConversations } from "../../hooks/useConversations";
import { useConversation } from "../../hooks/useConversation";
import { useAskStream } from "../../hooks/useAskStream";
import { Sidebar } from "./components/Sidebar";
import { MessageList, type Turn } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { ThinkingIndicator } from "./components/ThinkingIndicator";
import { ErrorState } from "./components/ErrorState";
import styles from "./ChatPage.module.css";

const USER_EMAIL = "duanne@mail.com"; // demo placeholder; real identity is a fast-follow

export default function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { conversations, refresh } = useConversations();
  const { detail } = useConversation(conversationId);
  const stream = useAskStream();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [lastQuestion, setLastQuestion] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load history when opening an existing conversation.
  useEffect(() => {
    if (detail) setTurns(detail.messages.map((m) => ({ role: m.role, content: m.content, citations: m.sources })));
    else if (!conversationId) setTurns([]);
  }, [detail, conversationId]);

  // Reflect the streaming answer into the last assistant turn.
  useEffect(() => {
    if (stream.status === "idle") return;
    setTurns((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, content: stream.answer, citations: stream.citations.length ? stream.citations : last.citations };
      }
      return next;
    });
  }, [stream.answer, stream.citations, stream.status]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, stream.status]);

  useEffect(() => {
    if (stream.status === "done") void refresh();
  }, [stream.status, refresh]);

  async function send(question: string) {
    setLastQuestion(question);
    setTurns((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "" }]);
    await stream.ask({ question, conversationId });
  }

  function newConversation() {
    setTurns([]);
    stream.reset();
    navigate("/oracle");
  }

  const streamingIndex = stream.status === "streaming" || stream.status === "thinking" ? turns.length - 1 : null;
  const showThinking = stream.status === "thinking";
  const showError = stream.status === "error";

  return (
    <div className={styles.shell}>
      <Sidebar
        conversations={conversations}
        activeId={conversationId ?? null}
        onNew={newConversation}
        onOpen={(id) => navigate(`/oracle/${id}`)}
        userEmail={USER_EMAIL}
      />
      <div className={styles.main}>
        <header className={styles.topbar}>
          <div>
            <strong>{turns.length ? "Conversa" : "Nova conversa"}</strong>
            <span className={styles.topSub}>● Respondendo só com fontes aprovadas do Notion</span>
          </div>
          <span className={styles.emailChip}>{USER_EMAIL}</span>
        </header>
        <div className={styles.thread} ref={scrollRef}>
          {turns.length === 0 && stream.status === "idle" ? (
            <EmptyState onPick={send} />
          ) : (
            <div className={styles.threadInner}>
              <MessageList turns={turns} streamingIndex={showThinking ? null : streamingIndex} />
              {showThinking && <ThinkingIndicator />}
              {showError && <ErrorState message={stream.errorMessage ?? "Erro ao gerar a resposta."} onRetry={() => send(lastQuestion)} />}
            </div>
          )}
        </div>
        <div className={styles.composerWrap}>
          <Composer onSend={send} disabled={stream.status === "thinking" || stream.status === "streaming"} />
          <p className={styles.composerNote}>O oráculo responde só com fontes aprovadas · nada confidencial</p>
        </div>
      </div>
    </div>
  );
}
