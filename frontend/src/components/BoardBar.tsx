"use client";

import { useState, type FormEvent } from "react";
import type { BoardSummary } from "@/lib/kanban";

type BoardBarProps = {
  boards: BoardSummary[];
  currentBoardId: string | null;
  disabled: boolean;
  onSelect: (boardId: string) => void;
  onCreate: (title: string) => Promise<boolean>;
  onRename: (boardId: string, title: string) => Promise<boolean>;
  onDelete: (boardId: string) => void;
};

export const BoardBar = ({
  boards,
  currentBoardId,
  disabled,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: BoardBarProps) => {
  const [mode, setMode] = useState<"idle" | "create" | "rename">("idle");
  const [draft, setDraft] = useState("");

  const currentBoard = boards.find((board) => board.id === currentBoardId) ?? null;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = draft.trim();
    if (!title) {
      return;
    }
    const success =
      mode === "create"
        ? await onCreate(title)
        : currentBoardId
          ? await onRename(currentBoardId, title)
          : false;
    if (success) {
      setMode("idle");
      setDraft("");
    }
  };

  return (
    <nav aria-label="Boards" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <ul className="flex flex-wrap items-center gap-2">
          {boards.map((board) => {
            const isActive = board.id === currentBoardId;
            return (
              <li key={board.id}>
                <button
                  type="button"
                  data-testid={`board-tab-${board.id}`}
                  aria-current={isActive ? "true" : undefined}
                  disabled={disabled}
                  onClick={() => onSelect(board.id)}
                  className={`rounded-full border px-4 py-2 text-sm font-semibold transition disabled:opacity-60 ${
                    isActive
                      ? "border-[var(--primary-blue)] bg-[var(--primary-blue)] text-white"
                      : "border-[var(--stroke)] bg-white/70 text-[var(--navy-dark)] hover:border-[var(--primary-blue)]"
                  }`}
                >
                  {board.title}
                </button>
              </li>
            );
          })}
        </ul>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("create");
              setDraft("");
            }}
            disabled={disabled}
            className="rounded-full border border-dashed border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] disabled:opacity-60"
          >
            + New board
          </button>
          {currentBoard ? (
            <>
              <button
                type="button"
                onClick={() => {
                  setMode("rename");
                  setDraft(currentBoard.title);
                }}
                disabled={disabled}
                className="rounded-full border border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] disabled:opacity-60"
              >
                Rename
              </button>
              <button
                type="button"
                onClick={() => onDelete(currentBoard.id)}
                disabled={disabled || boards.length <= 1}
                title={
                  boards.length <= 1 ? "You cannot delete your only board" : undefined
                }
                className="rounded-full border border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-red-700 transition hover:border-red-700 disabled:opacity-40"
              >
                Delete
              </button>
            </>
          ) : null}
        </div>
      </div>

      {mode !== "idle" ? (
        <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
          <label htmlFor="board-name-input" className="sr-only">
            {mode === "create" ? "New board name" : "Board name"}
          </label>
          <input
            id="board-name-input"
            autoFocus
            value={draft}
            maxLength={100}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Board name"
            className="min-w-[200px] rounded-xl border border-[var(--stroke)] bg-white px-4 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
          />
          <button
            type="submit"
            disabled={disabled || !draft.trim()}
            className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
          >
            {mode === "create" ? "Create board" : "Save name"}
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("idle");
              setDraft("");
            }}
            className="rounded-full border border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-[var(--navy-dark)]"
          >
            Cancel
          </button>
        </form>
      ) : null}
    </nav>
  );
};
