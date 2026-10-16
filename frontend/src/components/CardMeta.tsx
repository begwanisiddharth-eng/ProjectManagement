import type { Priority } from "@/lib/kanban";

const PRIORITY_STYLES: Record<Priority, string> = {
  low: "bg-[var(--surface)] text-[var(--gray-text)]",
  medium: "bg-[rgba(32,157,215,0.12)] text-[var(--primary-blue)]",
  high: "bg-[rgba(117,57,145,0.12)] text-[var(--secondary-purple)]",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

const formatDueDate = (value: string): string => {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

type CardMetaProps = {
  priority: Priority;
  dueDate: string | null;
};

export const CardMeta = ({ priority, dueDate }: CardMetaProps) => (
  <div className="flex flex-wrap items-center gap-2">
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${PRIORITY_STYLES[priority]}`}
    >
      {PRIORITY_LABELS[priority]}
    </span>
    {dueDate ? (
      <span
        className="rounded-full bg-[var(--surface)] px-2.5 py-1 text-xs font-semibold text-[var(--navy-dark)]"
        aria-label={`Due ${dueDate}`}
      >
        Due {formatDueDate(dueDate)}
      </span>
    ) : null}
  </div>
);
