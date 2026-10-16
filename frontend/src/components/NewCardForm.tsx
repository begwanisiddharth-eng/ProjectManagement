import { useState, type FormEvent } from "react";
import type { Priority } from "@/lib/kanban";

const initialFormState = {
  title: "",
  details: "",
  priority: "medium" as Priority,
  dueDate: "",
};

type NewCardFormProps = {
  onAdd: (
    title: string,
    details: string,
    priority: Priority,
    dueDate: string | null
  ) => Promise<boolean>;
  disabled: boolean;
};

export const NewCardForm = ({ onAdd, disabled }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim() || !formState.details.trim()) {
      return;
    }
    const added = await onAdd(
      formState.title.trim(),
      formState.details.trim(),
      formState.priority,
      formState.dueDate || null
    );
    if (added) {
      setFormState(initialFormState);
      setIsOpen(false);
    }
  };

  return (
    <div className="mt-4">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
            required
            disabled={disabled}
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            required
            disabled={disabled}
            rows={3}
            className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
          />
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1 text-xs font-semibold text-[var(--gray-text)]">
              Priority
              <select
                aria-label="Card priority"
                value={formState.priority}
                onChange={(event) =>
                  setFormState((prev) => ({
                    ...prev,
                    priority: event.target.value as Priority,
                  }))
                }
                disabled={disabled}
                className="rounded-lg border border-[var(--stroke)] bg-white px-2 py-1 text-sm text-[var(--navy-dark)]"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className="flex items-center gap-1 text-xs font-semibold text-[var(--gray-text)]">
              Due date
              <input
                type="date"
                aria-label="Card due date"
                value={formState.dueDate}
                onChange={(event) =>
                  setFormState((prev) => ({
                    ...prev,
                    dueDate: event.target.value,
                  }))
                }
                disabled={disabled}
                className="rounded-lg border border-[var(--stroke)] bg-white px-2 py-1 text-sm text-[var(--navy-dark)]"
              />
            </label>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
              disabled={
                disabled || !formState.title.trim() || !formState.details.trim()
              }
            >
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
              disabled={disabled}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="w-full rounded-full border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
          disabled={disabled}
        >
          Add a card
        </button>
      )}
    </div>
  );
};
