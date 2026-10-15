const API_BASE_URL =
  process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "";

export const apiFetch = (path: string, options?: RequestInit) =>
  fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
  });
