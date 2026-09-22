import "dotenv/config";
import fs from "node:fs";
import crypto from "node:crypto";
import { Client } from "pg";

const client = new Client({ connectionString: process.env.DATABASE_URL_UNPOOLED });

const migrationName = "0_init";
const migrationDir = `prisma/migrations/${migrationName}`;

async function main() {
  await client.connect();
  try {
    await client.query("BEGIN");
    const sql = fs.readFileSync(`${migrationDir}/migration.sql`, "utf8");
    await client.query(sql);
    await client.query(`
      CREATE TABLE IF NOT EXISTS _prisma_migrations (
        id TEXT PRIMARY KEY,
        checksum TEXT NOT NULL,
        finished_at TIMESTAMPTZ,
        migration_name TEXT NOT NULL,
        logs TEXT,
        rolled_back_at TIMESTAMPTZ,
        started_at TIMESTAMPTZ NOT NULL,
        applied_steps_count INTEGER NOT NULL DEFAULT 0
      )
    `);
    const checksum = crypto.createHash("sha256").update(sql).digest("hex");
    await client.query(
      `INSERT INTO _prisma_migrations (id, checksum, finished_at, migration_name, started_at, applied_steps_count)
       VALUES ($1, $2, now(), $3, now(), 1)
       ON CONFLICT (id) DO NOTHING`,
      [crypto.randomUUID(), checksum, migrationName]
    );
    await client.query("COMMIT");
    const tables = await client.query(
      `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name`
    );
    console.log("Tables:", tables.rows.map((r) => r.table_name).join(", "));
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    await client.end();
  }
}

main().catch((err) => {
  console.error("FAIL:", err.message);
  process.exit(1);
});