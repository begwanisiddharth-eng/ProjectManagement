import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

let board: BoardData;
let failNextColumnRename: boolean;
let failBoardLoad: boolean;

const response = (ok = true): Response =>
  ({
    ok,
    json: async () => JSON.parse(JSON.stringify(board)),
  }) as Response;

const getFirstColumn = async () =>
  (await screen.findAllByTestId(/column-/i))[0];

describe("KanbanBoard", () => {
  beforeEach(() => {
    board = JSON.parse(JSON.stringify(initialData)) as BoardData;
    failNextColumnRename = false;
    failBoardLoad = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        const method = init?.method ?? "GET";
        if (path === "/api/board" && method === "GET") {
          return response(!failBoardLoad);
        }
        if (path.startsWith("/api/board/columns/") && method === "PATCH") {
          if (failNextColumnRename) {
            failNextColumnRename = false;
            return response(false);
          }
          const columnId = path.split("/").at(-1);
          const body = JSON.parse(String(init?.body)) as { title: string };
          const column = board.columns.find((item) => item.id === columnId);
          if (column) {
            column.title = body.title;
          }
          return response();
        }
        if (path.includes("/cards") && method === "POST") {
          const columnId = path.split("/")[4];
          const body = JSON.parse(String(init?.body)) as {
            title: string;
            details: string;
          };
          const id = "test-card";
          board.cards[id] = { id, ...body };
          board.columns
            .find((column) => column.id === columnId)
            ?.cardIds.push(id);
          return response();
        }
        if (path.startsWith("/api/board/cards/") && method === "PATCH") {
          const cardId = path.split("/").at(-1);
          const body = JSON.parse(String(init?.body)) as {
            title: string;
            details: string;
          };
          if (cardId && board.cards[cardId]) {
            board.cards[cardId] = { id: cardId, ...body };
          }
          return response();
        }
        if (path.startsWith("/api/board/cards/") && method === "DELETE") {
          const cardId = path.split("/").at(-1);
          delete board.cards[cardId ?? ""];
          board.columns = board.columns.map((column) => ({
            ...column,
            cardIds: column.cardIds.filter((id) => id !== cardId),
          }));
          return response();
        }
        return response(false);
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the board from the API", async () => {
    render(<KanbanBoard />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading board");
    await expect(screen.findAllByTestId(/column-/i)).resolves.toHaveLength(5);
    expect(fetch).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("shows a load failure and retries", async () => {
    failBoardLoad = true;
    render(<KanbanBoard />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to load the board"
    );
    failBoardLoad = false;

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await getFirstColumn()).toBeInTheDocument();
  });

  it("renames a column after the API accepts the change", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    await userEvent.tab();

    await waitFor(() => expect(input).toHaveValue("New Name"));
    expect(fetch).toHaveBeenCalledWith(
      "/api/board/columns/col-backlog",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "New Name" }),
      })
    );
  });

  it("keeps the saved title when a rename fails and lets the user retry", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    failNextColumnRename = true;

    await userEvent.clear(input);
    await userEvent.type(input, "Rejected Name");
    await userEvent.tab();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to rename column"
    );
    await waitFor(() => expect(input).toHaveValue("Backlog"));

    await userEvent.clear(input);
    await userEvent.type(input, "Saved Name");
    await userEvent.tab();
    await waitFor(() => expect(input).toHaveValue("Saved Name"));
  });

  it("adds and removes a card through the API", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(await within(column).findByText("New card")).toBeInTheDocument();

    await userEvent.click(
      within(column).getByRole("button", { name: /delete new card/i })
    );
    await waitFor(() =>
      expect(within(column).queryByText("New card")).not.toBeInTheDocument()
    );
  });

  it("shows the empty-column state after its cards are removed", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();

    await userEvent.click(
      within(column).getByRole("button", {
        name: "Delete Align roadmap themes",
      })
    );
    await userEvent.click(
      within(column).getByRole("button", {
        name: "Delete Gather customer signals",
      })
    );

    expect(within(column).getByText("Drop a card here")).toBeInTheDocument();
  });

  it("edits a card through the API", async () => {
    render(<KanbanBoard />);
    const card = await screen.findByTestId("card-card-1");
    await userEvent.click(within(card).getByRole("button", { name: "Edit Align roadmap themes" }));
    await userEvent.clear(screen.getByRole("textbox", { name: "Card title" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Card title" }), "Updated roadmap");
    await userEvent.click(within(card).getByRole("button", { name: "Save" }));

    expect(await within(card).findByText("Updated roadmap")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "/api/board/cards/card-1",
      expect.objectContaining({ method: "PATCH" })
    );
  });
});
