import clsx from "clsx";
import { useState } from "react";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column, Priority } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  accent: string;
  onRename: (columnId: string, title: string) => Promise<boolean>;
  onAddCard: (
    columnId: string,
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) => Promise<boolean>;
  onDeleteCard: (cardId: string) => Promise<boolean>;
  onUpdateCard: (
    cardId: string,
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) => Promise<boolean>;
  isSaving: boolean;
};

export const KanbanColumn = ({
  column,
  cards,
  accent,
  onRename,
  onAddCard,
  onDeleteCard,
  onUpdateCard,
  isSaving,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    disabled: isSaving,
  });
  const [draft, setDraft] = useState({ value: column.title, forTitle: column.title });
  // Show the draft while editing, but fall back to column.title whenever it
  // changes externally (AI rename or board reload) so stale drafts are discarded.
  const title = draft.forTitle === column.title ? draft.value : column.title;

  const resetDraft = () => setDraft({ value: column.title, forTitle: column.title });

  const saveTitle = async () => {
    const nextTitle = title.trim();
    if (!nextTitle || nextTitle === column.title) {
      resetDraft();
      return;
    }
    if (!(await onRename(column.id, nextTitle))) {
      resetDraft();
    }
  };

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[520px] flex-col overflow-hidden rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] shadow-[var(--shadow)] transition",
        isOver && "ring-2 ring-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="h-1.5 w-full" style={{ backgroundColor: accent }} />
      <div className="flex flex-col p-4">
        <div className="flex items-center gap-2">
          <input
            value={title}
            onChange={(event) =>
              setDraft({ value: event.target.value, forTitle: column.title })
            }
            onBlur={saveTitle}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.currentTarget.blur();
              }
            }}
            disabled={isSaving}
            className="min-w-0 flex-1 rounded-lg bg-transparent px-1 py-0.5 font-display text-lg font-semibold text-[var(--navy-dark)] outline-none transition focus:bg-[var(--surface)]"
            aria-label="Column title"
          />
          <span className="shrink-0 rounded-full bg-[var(--surface)] px-2.5 py-1 text-xs font-semibold tabular-nums text-[var(--gray-text)]">
            {cards.length}
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 px-4 pb-4">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={onDeleteCard}
              onUpdate={onUpdateCard}
              disabled={isSaving}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <div className="px-4 pb-4">
        <NewCardForm
          onAdd={(title, details, priority, dueDate) =>
            onAddCard(column.id, title, details, priority, dueDate)
          }
          disabled={isSaving}
        />
      </div>
    </section>
  );
};
