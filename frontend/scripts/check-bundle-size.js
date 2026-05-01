#!/usr/bin/env node
// Bundle size guard for CI (audit-fixes I-007).
//
// Inspects frontend/dist/assets/*.js after `npm run build` and fails CI when:
//   * a non-worker chunk exceeds NON_WORKER_RAW_LIMIT or NON_WORKER_GZIP_LIMIT, or
//   * a worker chunk exceeds WORKER_RAW_LIMIT.
//
// Thresholds were calibrated against the actual 2026-05-01 build:
//   - largest non-worker entry: 741 KB raw / 248 KB gzip (`index-*.js`)
//   - largest worker:           7,020 KB raw (`ts.worker-*.js`)
// Limits leave ~35% headroom on the main entry and ~14% on ts.worker; tighten
// once the codebase stabilises.

import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.resolve(__dirname, "..", "dist", "assets");

const NON_WORKER_RAW_LIMIT = 1_000 * 1024; // 1,000 KB raw
const NON_WORKER_GZIP_LIMIT = 350 * 1024; // 350 KB gzip
const WORKER_RAW_LIMIT = 8 * 1024 * 1024; // 8 MB raw (Monaco language workers)

const WORKER_PATTERN = /\.worker-[^.]+\.js$/;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function gzipSize(filePath) {
  const buf = fs.readFileSync(filePath);
  return zlib.gzipSync(buf, { level: 9 }).length;
}

function main() {
  if (!fs.existsSync(ASSETS_DIR)) {
    console.error(
      `[bundle-size] ${ASSETS_DIR} not found. Run \`npm run build\` first.`,
    );
    process.exit(2);
  }

  const jsFiles = fs
    .readdirSync(ASSETS_DIR)
    .filter((name) => name.endsWith(".js"))
    .sort();

  if (jsFiles.length === 0) {
    console.error("[bundle-size] no .js files in dist/assets — build empty?");
    process.exit(2);
  }

  const rows = [];
  const failures = [];

  for (const name of jsFiles) {
    const full = path.join(ASSETS_DIR, name);
    const raw = fs.statSync(full).size;
    const isWorker = WORKER_PATTERN.test(name);
    const gzip = isWorker ? null : gzipSize(full);

    let status = "OK";
    if (isWorker) {
      if (raw > WORKER_RAW_LIMIT) {
        status = "FAIL";
        failures.push(
          `${name}: worker raw ${formatBytes(raw)} > ${formatBytes(WORKER_RAW_LIMIT)}`,
        );
      }
    } else {
      if (raw > NON_WORKER_RAW_LIMIT) {
        status = "FAIL";
        failures.push(
          `${name}: raw ${formatBytes(raw)} > ${formatBytes(NON_WORKER_RAW_LIMIT)}`,
        );
      }
      if (gzip !== null && gzip > NON_WORKER_GZIP_LIMIT) {
        status = "FAIL";
        failures.push(
          `${name}: gzip ${formatBytes(gzip)} > ${formatBytes(NON_WORKER_GZIP_LIMIT)}`,
        );
      }
    }

    rows.push({
      name,
      kind: isWorker ? "worker" : "chunk",
      raw,
      gzip,
      status,
    });
  }

  const nameWidth = Math.max(8, ...rows.map((r) => r.name.length));
  const header =
    `${"file".padEnd(nameWidth)}  ${"kind".padEnd(7)}  ${"raw".padStart(10)}  ${"gzip".padStart(10)}  status`;
  console.log(header);
  console.log("-".repeat(header.length));
  for (const r of rows) {
    console.log(
      `${r.name.padEnd(nameWidth)}  ${r.kind.padEnd(7)}  ` +
        `${formatBytes(r.raw).padStart(10)}  ` +
        `${(r.gzip === null ? "—" : formatBytes(r.gzip)).padStart(10)}  ` +
        r.status,
    );
  }

  console.log("");
  console.log(
    `Limits: non-worker raw ≤ ${formatBytes(NON_WORKER_RAW_LIMIT)}, ` +
      `gzip ≤ ${formatBytes(NON_WORKER_GZIP_LIMIT)}; ` +
      `worker raw ≤ ${formatBytes(WORKER_RAW_LIMIT)}`,
  );

  if (failures.length > 0) {
    console.error("");
    console.error(`[bundle-size] ${failures.length} chunk(s) over limit:`);
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }

  console.log("[bundle-size] all chunks within limits.");
}

main();
