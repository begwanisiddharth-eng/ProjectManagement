import { expect, test } from "@playwright/test";

const columns = '[data-testid^="column-"]';

test.beforeEach(async ({ page }) => {
  await page.goto("/login/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator(columns)).toHaveCount(5);
});

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(columns)).toHaveCount(5);
  await expect(page.getByRole("button", { name: "Board chat" })).toBeVisible();
});

test("creates a second board and switches between boards", async ({ page }) => {
  await page.goto("/");
  const name = `Launch ${Date.now()}`;
  await page.getByRole("button", { name: "+ New board" }).click();
  await page.getByLabel("New board name").fill(name);
  await page.getByRole("button", { name: "Create board" }).click();

  const newTab = page.getByRole("button", { name });
  await expect(newTab).toHaveAttribute("aria-current", "true");
  // The brand-new board starts empty.
  await expect(page.locator('[data-testid^="card-"]')).toHaveCount(0);

  // Switching back to the seeded board shows its cards again.
  await page.getByRole("button", { name: "Kanban Studio" }).click();
  await expect(page.getByTestId("card-card-1")).toBeVisible();
});

test("shows an assistant reply and applies its returned board update", async ({
  page,
}) => {
  await page.goto("/");
  const boardsResponse = await page.request.get("/api/boards");
  const boardsList = (await boardsResponse.json()) as { id: string }[];
  const boardId = boardsList[0].id;
  const boardResponse = await page.request.get(`/api/boards/${boardId}`);
  const board = (await boardResponse.json()) as {
    columns: unknown[];
    cards: Record<string, { id: string; title: string; details: string }>;
  };
  board.cards["card-1"].title = "Roadmap updated by assistant";
  board.columns[4] = {
    ...board.columns[4],
    title: "Finished by assistant",
  };
  await page.route("**/api/boards/*/chat", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        reply: "I renamed the roadmap card.",
        changed: true,
        board,
      }),
    })
  );

  await page.getByRole("button", { name: "Board chat" }).click();
  await page.getByRole("textbox", { name: "Ask the board assistant" }).fill(
    "Rename the roadmap card"
  );
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("I renamed the roadmap card.")).toBeVisible();
  await expect(page.getByText("Roadmap updated by assistant")).toBeVisible();
  await expect(
    page
      .getByTestId("column-col-done")
      .getByRole("textbox", { name: "Column title" })
  ).toHaveValue("Finished by assistant");
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  const firstColumn = page.locator(columns).first();
  const title = `Playwright card ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  const details = firstColumn.getByPlaceholder("Details");
  await expect(details).toHaveAttribute("required", "");
  await expect(firstColumn.getByRole("button", { name: /add card/i })).toBeDisabled();
  await details.fill("Added via e2e.");
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
  await page.route("**/api/boards/*/columns/col-backlog", (route) =>
    route.fulfill({ status: 500, body: "save failed" })
  );

  await titleInput.fill("Rejected title");
  await titleInput.press("Enter");
  await expect(page.locator("p[role='alert']")).toContainText(
    "Unable to rename column"
  );
  await expect(titleInput).toHaveValue(savedTitle);

  await page.unroute("**/api/boards/*/columns/col-backlog");
  await titleInput.fill("Retried title");
  await titleInput.press("Enter");
  await expect(titleInput).toHaveValue("Retried title");
});

test("adds and checks off a checklist item that persists after reload", async ({
  page,
}) => {
  await page.goto("/");
  const card = page.getByTestId("card-card-1");
  const text = `Checklist step ${Date.now()}`;

  await card.getByLabel("New checklist item").fill(text);
  await card.getByRole("button", { name: "Add" }).click();

  const checkbox = card.getByRole("checkbox", { name: text });
  await expect(checkbox).toBeVisible();
  await expect(card.getByText("Checklist 0/1")).toBeVisible();
  // The checkbox is controlled and reverts until the save round-trips, so click
  // it (without check()'s immediate state assertion) and wait on the progress.
  await checkbox.click();
  await expect(card.getByText("Checklist 1/1")).toBeVisible();

  await page.reload();
  const reloaded = page.getByTestId("card-card-1");
  await expect(reloaded.getByRole("checkbox", { name: text })).toBeChecked();

  await reloaded.getByRole("button", { name: `Remove ${text}` }).click();
  await expect(reloaded.getByText(text)).toHaveCount(0);
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
