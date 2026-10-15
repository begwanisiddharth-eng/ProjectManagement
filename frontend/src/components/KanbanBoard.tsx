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
import { apiFetch } from "@/lib/api";
import { moveCard, type BoardData } from "@/lib/kanban";

export const KanbanBoard = () => {
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
    apiFetch("/api/board")
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
  }, [loadAttempt]);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

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
        apiFetch(`/api/board/cards/${encodeURIComponent(cardId)}/move`, {
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
        apiFetch(`/api/board/columns/${encodeURIComponent(columnId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title.trim() }),
        }),
      "Unable to rename column. The board was not changed."
    );

  const handleAddCard = (columnId: string, title: string, details: string) =>
    saveBoardChange(
      () =>
        apiFetch(
          `/api/board/columns/${encodeURIComponent(columnId)}/cards`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, details }),
          }
        ),
      "Unable to add card. The board was not changed."
    );

  const handleUpdateCard = (cardId: string, title: string, details: string) =>
    saveBoardChange(
      () =>
        apiFetch(`/api/board/cards/${encodeURIComponent(cardId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, details }),
        }),
      "Unable to update card. The board was not changed."
    );

  const handleDeleteCard = (cardId: string) =>
    saveBoardChange(
      () =>
        apiFetch(`/api/board/cards/${encodeURIComponent(cardId)}`, {
          method: "DELETE",
        }),
      "Unable to remove card. The board was not changed."
    );

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

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4">
              {board.columns.map((column) => (
                <div
                  key={column.id}
                  className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
                >
                  <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                  {column.title}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              {logoutError ? (
                <p role="alert" className="text-sm text-red-700">
                  {logoutError}
                </p>
              ) : null}
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)]"
              >
                Sign out
              </button>
            </div>
          </div>
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
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onUpdateCard={handleUpdateCard}
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
