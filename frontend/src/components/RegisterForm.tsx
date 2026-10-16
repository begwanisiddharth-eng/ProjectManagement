"use client";

import { useState, type FormEvent } from "react";
import { apiFetch } from "@/lib/api";

export const RegisterForm = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (username.trim().length < 3) {
      setError("Choose a username with at least 3 characters.");
      return;
    }
    if (password.length < 8) {
      setError("Choose a password with at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("The passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await apiFetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      if (!response.ok) {
        setError(
          response.status === 409
            ? "That username is already taken."
            : "Unable to create your account. Please try again."
        );
        return;
      }

      window.location.assign("/");
    } catch {
      setError("Unable to reach the server. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <section className="w-full max-w-md rounded-[32px] border border-[var(--stroke)] bg-white/90 p-8 shadow-[var(--shadow)]">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
          Kanban Studio
        </p>
        <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
          Create your account
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
          Sign up to start organizing your project boards.
        </p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <label className="block text-sm font-medium text-[var(--navy-dark)]">
            Username
            <input
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 outline-none focus:border-[var(--primary-blue)]"
            />
          </label>
          <label className="block text-sm font-medium text-[var(--navy-dark)]">
            Password
            <input
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 outline-none focus:border-[var(--primary-blue)]"
            />
          </label>
          <label className="block text-sm font-medium text-[var(--navy-dark)]">
            Confirm password
            <input
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 outline-none focus:border-[var(--primary-blue)]"
            />
          </label>
          {error ? (
            <p role="alert" className="text-sm font-medium text-red-700">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-wait disabled:opacity-70"
          >
            {isSubmitting ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-[var(--gray-text)]">
          Already have an account?{" "}
          <a
            href="/login/"
            className="font-semibold text-[var(--primary-blue)] hover:underline"
          >
            Sign in
          </a>
        </p>
      </section>
    </main>
  );
};
