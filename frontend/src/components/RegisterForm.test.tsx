import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { RegisterForm } from "@/components/RegisterForm";

let assignedUrl: string;

beforeEach(() => {
  assignedUrl = "";
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { assign: (url: string) => (assignedUrl = url) } as Location,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it("registers and redirects to the board on success", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, status: 201 }) as Response);
  vi.stubGlobal("fetch", fetchMock);

  render(<RegisterForm />);
  await userEvent.type(screen.getByLabelText("Username"), "newuser");
  await userEvent.type(screen.getByLabelText("Password"), "supersecret");
  await userEvent.type(screen.getByLabelText("Confirm password"), "supersecret");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/auth/register",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ username: "newuser", password: "supersecret" }),
    })
  );
  expect(assignedUrl).toBe("/");
});

it("rejects mismatched passwords without calling the API", async () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);

  render(<RegisterForm />);
  await userEvent.type(screen.getByLabelText("Username"), "newuser");
  await userEvent.type(screen.getByLabelText("Password"), "supersecret");
  await userEvent.type(screen.getByLabelText("Confirm password"), "different1");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "passwords do not match"
  );
  expect(fetchMock).not.toHaveBeenCalled();
});

it("surfaces a taken username", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: false, status: 409 }) as Response)
  );

  render(<RegisterForm />);
  await userEvent.type(screen.getByLabelText("Username"), "taken");
  await userEvent.type(screen.getByLabelText("Password"), "supersecret");
  await userEvent.type(screen.getByLabelText("Confirm password"), "supersecret");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "already taken"
  );
});

it("rejects a short password before calling the API", async () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);

  render(<RegisterForm />);
  await userEvent.type(screen.getByLabelText("Username"), "newuser");
  await userEvent.type(screen.getByLabelText("Password"), "short");
  await userEvent.type(screen.getByLabelText("Confirm password"), "short");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "at least 8 characters"
  );
  expect(fetchMock).not.toHaveBeenCalled();
});
