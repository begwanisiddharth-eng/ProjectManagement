import { rm } from "node:fs/promises";
import { testDatabasePath } from "./test-database";

export default async function globalTeardown() {
  await rm(testDatabasePath, { force: true });
  await rm(`${testDatabasePath}-journal`, { force: true });
  await rm(`${testDatabasePath}-wal`, { force: true });
  await rm(`${testDatabasePath}-shm`, { force: true });
}
