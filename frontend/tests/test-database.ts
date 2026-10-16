import os from "node:os";
import path from "node:path";

export const testDatabasePath = path.join(
  os.tmpdir(),
  `kanban-playwright-${process.pid}.sqlite3`
);
