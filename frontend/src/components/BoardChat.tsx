"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type AIChatResponse = {
  reply: string;
  board: BoardData;
};

type BoardChatProps = {
  disabled: boolean;
  onBoardUpdate: (board: BoardData) => void;
  onBusyChange: (busy: boolean) => void;
};

export const BoardChat = ({
  disabled,
  onBoardUpdate,
  onBusyChange,
}: BoardChatProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [error, setError] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const conversationRef = useRef<HTMLDivElement>(null);
  const isPending = pendingQuestion !== "";

  useEffect(() => {
    if (conversationRef.current) {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
    }
  }, [messages, pendingQuestion]);

  const submitQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = draft.trim();
    if (!question || isPending || disabled) {
      return;
    }

    setPendingQuestion(question);
    setDraft("");
    setError("");
    onBusyChange(true);

    try {
      const response = await apiFetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          history: messages.slice(-20),
        }),
      });
      if (!response.ok) {
        const failure: { detail?: string } = await response.json();
        throw new Error(
          failure.detail || "The assistant could not answer. Please try again."
        );
      }

      const result: AIChatResponse = await response.json();
      setMessages((current) => [
        ...current,
        { role: "user", content: question },
        { role: "assistant", content: result.reply },
      ]);
      onBoardUpdate(result.board);
    } catch (caught) {
      setDraft(question);
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to reach the assistant. Please try again."
      );
    } finally {
      setPendingQuestion("");
      onBusyChange(false);
    }
  };

  return (
    <>
      <aside
        id="board-chat-panel"
        className={`min-w-0 flex-col overflow-hidden rounded-[32px] border border-[var(--stroke)] bg-white/90 shadow-[var(--shadow)] backdrop-blur ${
          isOpen
            ? "fixed inset-x-4 bottom-4 z-50 flex h-[min(680px,85vh)] min-h-[400px] sm:inset-x-auto sm:right-5 sm:w-[380px] min-[1400px]:sticky min-[1400px]:inset-auto min-[1400px]:top-8 min-[1400px]:h-full min-[1400px]:min-h-[520px]"
            : "hidden min-[1400px]:sticky min-[1400px]:top-8 min-[1400px]:flex min-[1400px]:h-full min-[1400px]:min-h-[520px]"
        }`}
      >
        <header className="flex items-start justify-between gap-3 border-b border-[var(--stroke)] px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
              AI assistant
            </p>
            <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
              Board chat
            </h2>
            <p className="mt-2 text-sm leading-5 text-[var(--gray-text)]">
              Ask questions or request card updates in plain language.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="rounded-full border border-[var(--stroke)] px-3 py-1.5 text-xs font-semibold text-[var(--navy-dark)] min-[1400px]:hidden"
            aria-label="Close board chat"
          >
            Close
          </button>
        </header>

        <div
          ref={conversationRef}
          role="log"
          aria-label="Chat conversation"
          aria-live="polite"
          className="flex flex-1 flex-col gap-3 overflow-y-auto px-5 py-5"
        >
          {messages.length === 0 && !pendingQuestion ? (
            <p className="rounded-2xl bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--gray-text)]">
              Try “Move the analytics prototype to Review” or ask what is in
              progress.
            </p>
          ) : null}
          {messages.map((message, index) => (
            <p
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-6 rounded-2xl bg-[var(--navy-dark)] px-4 py-3 text-sm leading-6 text-white"
                  : "mr-4 rounded-2xl bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--navy-dark)]"
              }
            >
              {message.content}
            </p>
          ))}
          {pendingQuestion ? (
            <>
              <p className="ml-6 rounded-2xl bg-[var(--navy-dark)] px-4 py-3 text-sm leading-6 text-white">
                {pendingQuestion}
              </p>
              <p role="status" className="mr-4 rounded-2xl bg-[var(--surface)] px-4 py-3 text-sm text-[var(--gray-text)]">
                Thinking...
              </p>
            </>
          ) : null}
        </div>

        <form onSubmit={submitQuestion} className="border-t border-[var(--stroke)] p-4">
          {error ? (
            <p role="alert" className="mb-3 text-sm leading-5 text-red-700">
              {error}
            </p>
          ) : null}
          <label htmlFor="board-chat-input" className="sr-only">
            Ask the board assistant
          </label>
          <textarea
            id="board-chat-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            maxLength={2000}
            rows={3}
            placeholder="Ask about your board..."
            disabled={disabled || isPending}
            className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm leading-5 text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] disabled:opacity-60"
          />
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="text-xs text-[var(--gray-text)]">
              Enter to send · Shift+Enter for a new line
            </span>
            <button
              type="submit"
              disabled={disabled || isPending || !draft.trim()}
              className="shrink-0 rounded-full bg-[var(--secondary-purple)] px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </form>
      </aside>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-expanded={isOpen}
        aria-controls="board-chat-panel"
        className={`fixed bottom-5 right-5 z-40 rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow)] transition hover:brightness-110 min-[1400px]:hidden ${
          isOpen ? "hidden" : ""
        }`}
      >
        Board chat
      </button>
    </>
  );
};
