import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import type { BoardData, BoardSummary } from "@/lib/kanban";

const BOARD_ID = "board-1";

const initialData: BoardData = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-4", "card-5"] },
    { id: "col-review", title: "Review", cardIds: ["card-6"] },
    { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Align roadmap themes", details: "Draft quarterly themes." },
    "card-2": { id: "card-2", title: "Gather customer signals", details: "Review support tags." },
    "card-3": { id: "card-3", title: "Prototype analytics view", details: "Sketch dashboard layout." },
    "card-4": { id: "card-4", title: "Refine status language", details: "Standardize column labels." },
    "card-5": { id: "card-5", title: "Design card layout", details: "Add hierarchy and spacing." },
    "card-6": { id: "card-6", title: "QA micro-interactions", details: "Verify hover and focus states." },
    "card-7": { id: "card-7", title: "Ship marketing page", details: "Final copy approved." },
    "card-8": { id: "card-8", title: "Close onboarding sprint", details: "Document release notes." },
  },
};

let board: BoardData;
let boards: BoardSummary[];
let failNextColumnRename: boolean;
let failBoardLoad: boolean;
let failAIChat: boolean;
let aiChatRequest: { question: string; history: unknown[] } | null;
let aiChatPath: string | null;

const summary = (id: string, title: string): BoardSummary => ({
  id,
  title,
  createdAt: "2026-01-01T00:00:00+00:00",
  updatedAt: "2026-01-01T00:00:00+00:00",
});

const boardResponse = (ok = true): Response =>
  ({
    ok,
    status: ok ? 200 : 500,
    json: async () => JSON.parse(JSON.stringify(board)),
  }) as Response;

const jsonResponse = (ok: boolean, status: number, body: unknown): Response =>
  ({
    ok,
    status,
    json: async () => JSON.parse(JSON.stringify(body)),
  }) as Response;

const getFirstColumn = async () =>
  (await screen.findAllByTestId(/column-/i))[0];

const routeFetch = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> => {
  const path = String(input);
  const method = init?.method ?? "GET";

  if (path === "/api/boards" && method === "GET") {
    return jsonResponse(true, 200, boards);
  }
  if (path === "/api/boards" && method === "POST") {
    const body = JSON.parse(String(init?.body)) as { title: string };
    const created = summary(`board-${boards.length + 1}`, body.title);
    boards = [...boards, created];
    return jsonResponse(true, 201, created);
  }

  if (path.startsWith("/api/boards/")) {
    const segments = path.slice("/api/boards/".length).split("/");
    if (segments.length === 1) {
      if (method === "GET") {
        return boardResponse(!failBoardLoad);
      }
      if (method === "PATCH") {
        const body = JSON.parse(String(init?.body)) as { title: string };
        boards = boards.map((item) =>
          item.id === segments[0] ? { ...item, title: body.title } : item
        );
        return jsonResponse(true, 200, { ...summary(segments[0], body.title) });
      }
      if (method === "DELETE") {
        if (boards.length <= 1) {
          return jsonResponse(false, 409, { detail: "last board" });
        }
        boards = boards.filter((item) => item.id !== segments[0]);
        return jsonResponse(true, 204, {});
      }
    }
    if (segments[1] === "chat" && method === "POST") {
      aiChatPath = path;
      aiChatRequest = JSON.parse(String(init?.body)) as {
        question: string;
        history: unknown[];
      };
      if (failAIChat) {
        return jsonResponse(false, 502, { detail: "Assistant is not configured." });
      }
      board.cards["card-1"].title = "Roadmap refined by AI";
      board.columns[4].title = "Finished by AI";
      return jsonResponse(true, 200, {
        reply: "I updated the roadmap card.",
        board: JSON.parse(JSON.stringify(board)),
      });
    }
    if (segments[1] === "columns" && segments.length === 3 && method === "PATCH") {
      if (failNextColumnRename) {
        failNextColumnRename = false;
        return boardResponse(false);
      }
      const body = JSON.parse(String(init?.body)) as { title: string };
      const column = board.columns.find((item) => item.id === segments[2]);
      if (column) {
        column.title = body.title;
      }
      return boardResponse();
    }
    if (
      segments[1] === "columns" &&
      segments[3] === "cards" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body)) as {
        title: string;
        details: string;
      };
      const id = "test-card";
      board.cards[id] = { id, ...body };
      board.columns.find((column) => column.id === segments[2])?.cardIds.push(id);
      return boardResponse();
    }
    if (segments[1] === "cards" && method === "PATCH" && segments.length === 3) {
      const cardId = segments[2];
      const body = JSON.parse(String(init?.body)) as {
        title: string;
        details: string;
      };
      if (board.cards[cardId]) {
        board.cards[cardId] = { id: cardId, ...body };
      }
      return boardResponse();
    }
    if (segments[1] === "cards" && method === "DELETE") {
      const cardId = segments[2];
      delete board.cards[cardId];
      board.columns = board.columns.map((column) => ({
        ...column,
        cardIds: column.cardIds.filter((id) => id !== cardId),
      }));
      return boardResponse();
    }
  }

  return boardResponse(false);
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    board = JSON.parse(JSON.stringify(initialData)) as BoardData;
    boards = [summary(BOARD_ID, "Kanban Studio")];
    failNextColumnRename = false;
    failBoardLoad = false;
    failAIChat = false;
    aiChatRequest = null;
    aiChatPath = null;
    vi.stubGlobal("fetch", vi.fn(routeFetch));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the boards list and then the current board", async () => {
    render(<KanbanBoard />);
    await expect(screen.findAllByTestId(/column-/i)).resolves.toHaveLength(5);
    expect(fetch).toHaveBeenCalledWith(
      "/api/boards",
      expect.objectContaining({ credentials: "include" })
    );
    expect(fetch).toHaveBeenCalledWith(
      `/api/boards/${BOARD_ID}`,
      expect.objectContaining({ credentials: "include" })
    );
    expect(
      screen.getByTestId(`board-tab-${BOARD_ID}`)
    ).toHaveTextContent("Kanban Studio");
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

  it("creates a new board and switches to it", async () => {
    render(<KanbanBoard />);
    await getFirstColumn();

    await userEvent.click(screen.getByRole("button", { name: "+ New board" }));
    await userEvent.type(screen.getByLabelText("New board name"), "Marketing");
    await userEvent.click(screen.getByRole("button", { name: "Create board" }));

    const newTab = await screen.findByRole("button", { name: "Marketing" });
    await waitFor(() => expect(newTab).toHaveAttribute("aria-current", "true"));
    expect(fetch).toHaveBeenCalledWith(
      "/api/boards",
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api/boards/board-2",
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("renames the current board", async () => {
    render(<KanbanBoard />);
    await getFirstColumn();

    await userEvent.click(screen.getByRole("button", { name: "Rename" }));
    const input = screen.getByLabelText("Board name");
    await userEvent.clear(input);
    await userEvent.type(input, "Launch Plan");
    await userEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(
      await screen.findByRole("button", { name: "Launch Plan" })
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      `/api/boards/${BOARD_ID}`,
      expect.objectContaining({ method: "PATCH" })
    );
  });

  it("disables deleting the only board", async () => {
    render(<KanbanBoard />);
    await getFirstColumn();

    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
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
      `/api/boards/${BOARD_ID}/columns/col-backlog`,
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

  it("prevents adding a card without nonblank details", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    await userEvent.click(
      within(column).getByRole("button", { name: /add a card/i })
    );
    await userEvent.type(
      within(column).getByPlaceholderText(/card title/i),
      "Title only"
    );

    expect(
      within(column).getByRole("button", { name: /add card/i })
    ).toBeDisabled();
    await userEvent.type(
      within(column).getByPlaceholderText(/details/i),
      "   "
    );
    expect(
      within(column).getByRole("button", { name: /add card/i })
    ).toBeDisabled();
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/cards"),
      expect.objectContaining({ method: "POST" })
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
      `/api/boards/${BOARD_ID}/cards/card-1`,
      expect.objectContaining({ method: "PATCH" })
    );
  });

  it("sends a chat message and reflects the returned board without reloading", async () => {
    render(<KanbanBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Board chat" }));
    const input = await screen.findByRole("textbox", {
      name: "Ask the board assistant",
    });
    await userEvent.type(input, "Rename the roadmap card");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("I updated the roadmap card.")).toBeInTheDocument();
    expect(await screen.findByText("Roadmap refined by AI")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("column-col-done")).getByLabelText("Column title")
    ).toHaveValue("Finished by AI");
    expect(aiChatPath).toBe(`/api/boards/${BOARD_ID}/chat`);
    expect(aiChatRequest).toEqual({
      question: "Rename the roadmap card",
      history: [],
    });
  });

  it("prevents empty chat submissions", async () => {
    render(<KanbanBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Board chat" }));
    const sendButton = await screen.findByRole("button", { name: "Send" });

    expect(sendButton).toBeDisabled();
    expect(aiChatRequest).toBeNull();
  });

  it("shows the AI API error and keeps the question available to retry", async () => {
    failAIChat = true;
    render(<KanbanBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Board chat" }));
    const input = await screen.findByRole("textbox", {
      name: "Ask the board assistant",
    });
    await userEvent.type(input, "Move the analytics card");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Assistant is not configured."
    );
    expect(input).toHaveValue("Move the analytics card");
  });
});
