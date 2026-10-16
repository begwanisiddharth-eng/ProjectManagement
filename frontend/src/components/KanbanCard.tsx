"use client";

import { useState, type FormEvent } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => Promise<boolean>;
  onUpdate: (cardId: string, title: string, details: string) => Promise<boolean>;
  disabled: boolean;
};

export const KanbanCard = ({
  card,
  onDelete,
  onUpdate,
  disabled,
}: KanbanCardProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const { listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id, disabled: disabled || isEditing });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const handleUpdate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextTitle = title.trim();
    if (!nextTitle) {
      return;
    }
    if (await onUpdate(card.id, nextTitle, details.trim())) {
      setIsEditing(false);
    }
  };

  const cancelEditing = () => {
    setTitle(card.title);
    setDetails(card.details);
    setIsEditing(false);
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3.5 shadow-[0_6px_16px_rgba(3,33,71,0.06)]",
        "transition-all duration-150 hover:border-[rgba(32,157,215,0.4)] hover:shadow-[0_12px_24px_rgba(3,33,71,0.1)]",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      {isEditing ? (
        <form onSubmit={handleUpdate} className="space-y-3">
          <input
            aria-label="Card title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm font-semibold text-[var(--navy-dark)]"
            required
            disabled={disabled}
          />
          <textarea
            aria-label="Card details"
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            rows={3}
            className="w-full resize-none rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--gray-text)]"
            disabled={disabled}
          />
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white"
              disabled={disabled}
            >
              Save
            </button>
            <button
              type="button"
              onClick={cancelEditing}
              className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]"
              disabled={disabled}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="group flex min-w-0 flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <h4 className="min-w-0 break-words font-display text-base font-semibold leading-6 text-[var(--navy-dark)]">
              {card.title}
            </h4>
            <div className="flex shrink-0 gap-0.5 opacity-60 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="flex h-7 w-7 items-center justify-center rounded-full border border-transparent text-[var(--primary-blue)] transition hover:border-[var(--stroke)] hover:bg-[var(--surface)] focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-[var(--primary-blue)]"
                aria-label={`Edit ${card.title}`}
                disabled={disabled}
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-[18px] w-[18px]"
                >
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => void onDelete(card.id)}
                className="flex h-7 w-7 items-center justify-center rounded-full border border-transparent text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:bg-[var(--surface)] hover:text-red-600 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-[var(--primary-blue)]"
                aria-label={`Delete ${card.title}`}
                disabled={disabled}
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-[18px] w-[18px]"
                >
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="m19 6-1 14H6L5 6" />
                  <path d="M10 11v5M14 11v5" />
                </svg>
              </button>
            </div>
          </div>
          {card.details ? (
            <p className="min-w-0 break-words text-sm leading-6 text-[var(--gray-text)]">
              {card.details}
            </p>
          ) : null}
        </div>
      )}
    </article>
  );
};
