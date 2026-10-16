import { expect, test } from "@playwright/test";

const columns = '[data-testid^="column-"]';

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
  await expect(page.locator(columns)).toHaveCount(5);

  await page.reload();

  await expect(page.locator(columns)).toHaveCount(5);
});

test("registers a new account and lands on an empty board", async ({ page }) => {
  const username = `e2e-user-${Date.now()}`;
  await page.goto("/register/");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("supersecret");
  await page.getByLabel("Confirm password").fill("supersecret");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.locator(columns)).toHaveCount(5);
  await expect(page.locator('[data-testid^="card-"]')).toHaveCount(0);
});

test("sign out invalidates the session and hides the board", async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();

  await expect(page).toHaveURL(/\/login\/$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const sessionResponse = await page.request.get("/api/auth/session");
  expect(sessionResponse.status()).toBe(401);
});
