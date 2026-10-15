import { expect, test } from "@playwright/test";

test("redirects logged-out users to sign in", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/login\/$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("shows an error for invalid credentials", async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(
    page.getByText("Invalid username or password.", { exact: true })
  ).toBeVisible();
  await expect(page).toHaveURL(/\/login\/$/);
});

test("keeps a signed-in user authenticated after reload", async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("sign out invalidates the session and hides the board", async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();

  await expect(page).toHaveURL(/\/login\/$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const sessionResponse = await page.request.get("/api/auth/session");
  expect(sessionResponse.status()).toBe(401);
});
