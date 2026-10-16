"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { BoardChat } from "@/components/BoardChat";
import { BoardBar } from "@/components/BoardBar";
import { apiFetch } from "@/lib/api";
import {
  moveCard,
  type BoardData,
  type BoardSummary,
  type Priority,
} from "@/lib/kanban";

const COLUMN_ACCENTS = [
  "var(--accent-yellow)",
  "var(--primary-blue)",
  "var(--secondary-purple)",
  "var(--navy-dark)",
  "var(--gray-text)",
];

export const KanbanBoard = () => {
  const [boards, setBoards] = useState<BoardSummary[] | null>(null);
  const [currentBoardId, setCurrentBoardId] = useState<string | null>(null);
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [logoutError, setLogoutError] = useState("");
  const [boardError, setBoardError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isChatBusy, setIsChatBusy] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const savingRef = useRef(false);
  const chatBusyRef = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  useEffect(() => {
    let isMounted = true;
    apiFetch("/api/boards")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Unable to load your boards.");
        }
        const loadedBoards: BoardSummary[] = await response.json();
        if (isMounted) {
          setBoards(loadedBoards);
          setCurrentBoardId((current) =>
            current && loadedBoards.some((item) => item.id === current)
              ? current
              : (loadedBoards[0]?.id ?? null)
          );
          setBoardError("");
        }
      })
      .catch(() => {
        if (isMounted) {
          setBoardError("Unable to load your boards. Check the server and retry.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [loadAttempt]);

  useEffect(() => {
    if (!currentBoardId) {
      return;
    }
    let isMounted = true;
    setBoard(null);
    apiFetch(`/api/boards/${encodeURIComponent(currentBoardId)}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Unable to load the board.");
        }
        const loadedBoard: BoardData = await response.json();
        if (isMounted) {
          setBoard(loadedBoard);
          setBoardError("");
        }
      })
      .catch(() => {
        if (isMounted) {
          setBoardError("Unable to load the board. Check the server and retry.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [currentBoardId, loadAttempt]);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);
  const boardBasePath = currentBoardId
    ? `/api/boards/${encodeURIComponent(currentBoardId)}`
    : "";

  const cardPath = (cardId: string) =>
    `${boardBasePath}/cards/${encodeURIComponent(cardId)}`;

  const saveBoardChange = async (
    request: () => Promise<Response>,
    errorMessage: string
  ): Promise<boolean> => {
    if (savingRef.current || chatBusyRef.current) {
      return false;
    }
    savingRef.current = true;
    setIsSaving(true);
    setBoardError("");
    try {
      const response = await request();
      if (!response.ok) {
        throw new Error("The board update was rejected.");
      }
      const updatedBoard: BoardData = await response.json();
      setBoard(updatedBoard);
      return true;
    } catch {
      setBoardError(errorMessage);
      return false;
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id || !board || chatBusyRef.current) {
      return;
    }

    const cardId = String(active.id);
    const columns = moveCard(board.columns, cardId, String(over.id));
    if (
      columns.every((column, index) =>
        column.cardIds.length === board.columns[index].cardIds.length &&
        column.cardIds.every(
          (id, cardIndex) => id === board.columns[index].cardIds[cardIndex]
        )
      )
    ) {
      return;
    }
    const targetColumn = columns.find((column) =>
      column.cardIds.includes(cardId)
    );
    if (!targetColumn) {
      return;
    }
    void saveBoardChange(
      () =>
        apiFetch(`${cardPath(cardId)}/move`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            column_id: targetColumn.id,
            position: targetColumn.cardIds.indexOf(cardId),
          }),
        }),
      "Unable to move card. The board was not changed."
    );
  };

  const handleRenameColumn = (columnId: string, title: string) =>
    saveBoardChange(
      () =>
        apiFetch(`${boardBasePath}/columns/${encodeURIComponent(columnId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title.trim() }),
        }),
      "Unable to rename column. The board was not changed."
    );

  const handleAddCard = (
    columnId: string,
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) =>
    saveBoardChange(
      () =>
        apiFetch(
          `${boardBasePath}/columns/${encodeURIComponent(columnId)}/cards`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, details, priority, due_date: dueDate }),
          }
        ),
      "Unable to add card. The board was not changed."
    );

  const handleUpdateCard = (
    cardId: string,
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) =>
    saveBoardChange(
      () =>
        apiFetch(cardPath(cardId), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, details, priority, due_date: dueDate }),
        }),
      "Unable to update card. The board was not changed."
    );

  const handleDeleteCard = (cardId: string) =>
    saveBoardChange(
      () =>
        apiFetch(cardPath(cardId), { method: "DELETE" }),
      "Unable to remove card. The board was not changed."
    );

  const checklistHandlers = {
    onAdd: (cardId: string, text: string) =>
      saveBoardChange(
        () =>
          apiFetch(`${cardPath(cardId)}/checklist`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
          }),
        "Unable to add checklist item. The board was not changed."
      ),
    onToggle: (cardId: string, itemId: string, done: boolean) =>
      saveBoardChange(
        () =>
          apiFetch(
            `${cardPath(cardId)}/checklist/${encodeURIComponent(itemId)}`,
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ done }),
            }
          ),
        "Unable to update checklist item. The board was not changed."
      ),
    onRemove: (cardId: string, itemId: string) =>
      saveBoardChange(
        () =>
          apiFetch(
            `${cardPath(cardId)}/checklist/${encodeURIComponent(itemId)}`,
            { method: "DELETE" }
          ),
        "Unable to remove checklist item. The board was not changed."
      ),
  };

  const handleCreateBoard = async (title: string): Promise<boolean> => {
    setBoardError("");
    try {
      const response = await apiFetch("/api/boards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) {
        throw new Error("rejected");
      }
      const summary: BoardSummary = await response.json();
      setBoards((current) => [...(current ?? []), summary]);
      setCurrentBoardId(summary.id);
      return true;
    } catch {
      setBoardError("Unable to create the board. Please try again.");
      return false;
    }
  };

  const handleRenameBoard = async (
    boardId: string,
    title: string
  ): Promise<boolean> => {
    setBoardError("");
    try {
      const response = await apiFetch(
        `/api/boards/${encodeURIComponent(boardId)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title }),
        }
      );
      if (!response.ok) {
        throw new Error("rejected");
      }
      const summary: BoardSummary = await response.json();
      setBoards((current) =>
        (current ?? []).map((item) => (item.id === summary.id ? summary : item))
      );
      return true;
    } catch {
      setBoardError("Unable to rename the board. Please try again.");
      return false;
    }
  };

  const handleDeleteBoard = async (boardId: string) => {
    setBoardError("");
    try {
      const response = await apiFetch(
        `/api/boards/${encodeURIComponent(boardId)}`,
        { method: "DELETE" }
      );
      if (response.status === 409) {
        setBoardError("You cannot delete your only board.");
        return;
      }
      if (!response.ok) {
        throw new Error("rejected");
      }
      setBoards((current) => {
        const remaining = (current ?? []).filter((item) => item.id !== boardId);
        setCurrentBoardId((active) =>
          active === boardId ? (remaining[0]?.id ?? null) : active
        );
        return remaining;
      });
    } catch {
      setBoardError("Unable to delete the board. Please try again.");
    }
  };

  const handleRetryLoad = () => {
    setBoard(null);
    setBoardError("");
    setLoadAttempt((attempt) => attempt + 1);
  };

  const handleLogout = async () => {
    setLogoutError("");
    try {
      const response = await apiFetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        setLogoutError("Unable to sign out. Please try again.");
        return;
      }
      window.location.assign("/login/");
    } catch {
      setLogoutError("Unable to reach the server. Please try again.");
    }
  };

  if (!board) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6 text-center">
        {boardError ? (
          <div>
            <p role="alert" className="text-sm font-medium text-red-700">
              {boardError}
            </p>
            <button
              type="button"
              onClick={handleRetryLoad}
              className="mt-4 rounded-full border border-[var(--stroke)] px-4 py-2 text-sm font-semibold text-[var(--navy-dark)]"
            >
              Retry
            </button>
          </div>
        ) : (
          <p role="status" className="text-sm font-medium text-[var(--gray-text)]">
            Loading board...
          </p>
        )}
      </main>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const totalCards = Object.keys(board.cards).length;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-4 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-6 shadow-[var(--shadow)] backdrop-blur sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Kanban Studio
              </p>
              <div className="mt-3">
                <BoardBar
                  key={currentBoardId ?? "none"}
                  boards={boards ?? []}
                  currentBoardId={currentBoardId}
                  disabled={isSaving || isChatBusy}
                  onSelect={setCurrentBoardId}
                  onCreate={handleCreateBoard}
                  onRename={handleRenameBoard}
                  onDelete={handleDeleteBoard}
                />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2">
                <span className="text-lg font-semibold tabular-nums text-[var(--primary-blue)]">
                  {totalCards}
                </span>
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  {totalCards === 1 ? "card" : "cards"}
                </span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                >
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <path d="m16 17 5-5-5-5" />
                  <path d="M21 12H9" />
                </svg>
                Sign out
              </button>
            </div>
          </div>
          {logoutError ? (
            <p role="alert" className="text-sm font-medium text-red-700">
              {logoutError}
            </p>
          ) : null}
          {boardError ? (
            <p role="alert" className="text-sm font-medium text-red-700">
              {boardError}
            </p>
          ) : null}
        </header>

        <div className="grid items-stretch gap-6 min-[1400px]:grid-cols-[minmax(0,1fr)_340px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="flex gap-6 overflow-x-auto pb-2">
              {board.columns.map((column, index) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  accent={COLUMN_ACCENTS[index % COLUMN_ACCENTS.length]}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onUpdateCard={handleUpdateCard}
                  checklist={checklistHandlers}
                  isSaving={isSaving || isChatBusy}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
          <BoardChat
            boardId={currentBoardId ?? ""}
            disabled={isSaving}
            onBoardUpdate={setBoard}
            onBusyChange={(busy) => {
              chatBusyRef.current = busy;
              setIsChatBusy(busy);
            }}
          />
        </div>
      </main>
    </div>
  );
};
