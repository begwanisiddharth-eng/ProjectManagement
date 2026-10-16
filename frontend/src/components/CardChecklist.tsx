"use client";

import { useState, type FormEvent } from "react";
import type { Card, ChecklistHandlers } from "@/lib/kanban";

type CardChecklistProps = {
  card: Card;
  handlers: ChecklistHandlers;
  disabled: boolean;
};

export const CardChecklist = ({
  card,
  handlers,
  disabled,
}: CardChecklistProps) => {
  const [text, setText] = useState("");
  const items = card.checklist;
  const doneCount = items.filter((item) => item.done).length;

  const handleAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = text.trim();
    if (!next) {
      return;
    }
    if (await handlers.onAdd(card.id, next)) {
      setText("");
    }
  };

  return (
    <section className="flex flex-col gap-2" aria-label="Checklist">
      {items.length > 0 ? (
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
          Checklist {doneCount}/{items.length}
        </p>
      ) : null}
      <ul className="flex flex-col gap-1">
        {items.map((item) => (
          <li key={item.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={item.done}
              onChange={(event) =>
                void handlers.onToggle(card.id, item.id, event.target.checked)
              }
              disabled={disabled}
              className="h-4 w-4 shrink-0 accent-[var(--primary-blue)]"
              aria-label={item.text}
            />
            <span
              className={`min-w-0 flex-1 text-sm ${
                item.done
                  ? "text-[var(--gray-text)] line-through"
                  : "text-[var(--navy-dark)]"
              }`}
            >
              {item.text}
            </span>
            <button
              type="button"
              onClick={() => void handlers.onRemove(card.id, item.id)}
              disabled={disabled}
              className="shrink-0 text-xs font-semibold text-[var(--gray-text)] transition hover:text-red-600"
              aria-label={`Remove ${item.text}`}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Add checklist item"
          disabled={disabled}
          className="min-w-0 flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-sm text-[var(--navy-dark)]"
          aria-label="New checklist item"
        />
        <button
          type="submit"
          disabled={disabled}
          className="shrink-0 rounded-full border border-[var(--stroke)] px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)]"
        >
          Add
        </button>
      </form>
    </section>
  );
};
