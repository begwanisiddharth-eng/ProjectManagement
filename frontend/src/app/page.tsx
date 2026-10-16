"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { apiFetch } from "@/lib/api";

type SessionState = "checking" | "authenticated" | "unavailable";

export default function Home() {
  const [sessionState, setSessionState] = useState<SessionState>("checking");

  useEffect(() => {
    apiFetch("/api/auth/session")
      .then((response) => {
        if (response.status === 401) {
          window.location.replace("/login/");
          return;
        }
        if (!response.ok) {
          setSessionState("unavailable");
          return;
        }
        setSessionState("authenticated");
      })
      .catch(() => setSessionState("unavailable"));
  }, []);

  if (sessionState === "authenticated") {
    return <KanbanBoard />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 text-center">
      <p role="status" className="text-sm font-medium text-[var(--gray-text)]">
        {sessionState === "checking"
          ? "Checking your session..."
          : "Unable to verify your session. Check the server and try again."}
      </p>
    </main>
  );
}
