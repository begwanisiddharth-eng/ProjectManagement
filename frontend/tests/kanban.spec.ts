import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const title = `Playwright card ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(title)).toBeVisible();

  await page.reload();
  const savedCard = page.getByText(title);
  await expect(savedCard).toBeVisible();
  const savedCardContainer = page.locator('[data-testid^="card-"]').filter({
    has: page.getByText(title),
  });
  await savedCardContainer.getByRole("button", { name: `Delete ${title}` }).click();
});

test("edits card details and persists the update after reload", async ({ page }) => {
  await page.goto("/");
  const card = page.getByTestId("card-card-1");
  await card.getByRole("button", { name: "Edit Align roadmap themes" }).click();
  await card.getByRole("textbox", { name: "Card title" }).fill("Updated roadmap");
  await card.getByRole("textbox", { name: "Card details" }).fill("Saved details.");
  await card.getByRole("button", { name: "Save" }).click();
  await expect(card.getByText("Updated roadmap")).toBeVisible();

  await page.reload();
  const updatedCard = page.getByTestId("card-card-1");
  await expect(updatedCard.getByText("Updated roadmap")).toBeVisible();
  await expect(updatedCard.getByText("Saved details.")).toBeVisible();
});

test("persists a column rename after reload", async ({ page }) => {
  await page.goto("/");
  const titleInput = page
    .getByTestId("column-col-backlog")
    .getByRole("textbox", { name: "Column title" });
  await titleInput.fill("Priorities");
  await titleInput.press("Enter");
  await expect(titleInput).toHaveValue("Priorities");

  await page.reload();
  await expect(
    page.getByTestId("column-col-backlog").getByRole("textbox", {
      name: "Column title",
    })
  ).toHaveValue("Priorities");
});

test("shows failed saves and allows retrying the change", async ({ page }) => {
  await page.goto("/");
  const titleInput = page
    .getByTestId("column-col-backlog")
    .getByRole("textbox", { name: "Column title" });
  const savedTitle = await titleInput.inputValue();
  await page.route("**/api/board/columns/col-backlog", (route) =>
    route.fulfill({ status: 500, body: "save failed" })
  );

  await titleInput.fill("Rejected title");
  await titleInput.press("Enter");
  await expect(page.locator("p[role='alert']")).toContainText(
    "Unable to rename column"
  );
  await expect(titleInput).toHaveValue(savedTitle);

  await page.unroute("**/api/board/columns/col-backlog");
  await titleInput.fill("Retried title");
  await titleInput.press("Enter");
  await expect(titleInput).toHaveValue("Retried title");
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();

  await page.reload();
  await expect(
    page.getByTestId("column-col-review").getByTestId("card-card-1")
  ).toBeVisible();
});
