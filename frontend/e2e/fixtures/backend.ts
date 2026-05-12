/**
 * Playwright globalSetup: spin up an isolated backend instance for the e2e run.
 *
 * Strategy:
 * 1. Allocate a temp SQLite file (`/tmp/coderecall-e2e-${pid}-${ts}.db`).
 * 2. Run `alembic upgrade head` synchronously against that DB.
 * 3. Pick a free port on 127.0.0.1 by binding to :0 and reading the assigned port.
 * 4. Spawn `uvicorn app.main:app` against that port + tmp DB, with secure-but-fixed test
 *    credentials and AI disabled.
 * 5. Poll `/health` until 200 (max 30s).
 * 6. Expose `E2E_BACKEND_URL` via `process.env` so specs and the auth fixture can read it.
 * 7. Return an async cleanup that SIGTERMs the process, falls back to SIGKILL after 2s,
 *    and unlinks the tmp DB.
 *
 * Single uvicorn instance is shared by all specs because Playwright workers default to 1
 * (see playwright.config.ts) and registering a fresh user per spec gives sufficient isolation
 * for the MVP scope.
 */
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const REPO_ROOT = resolve(__dirname, "..", "..", "..");
const BACKEND_DIR = join(REPO_ROOT, "backend");
const VENV_PYTHON = join(BACKEND_DIR, ".venv", "bin", "python");

const HEALTH_TIMEOUT_MS = 30_000;
const HEALTH_POLL_INTERVAL_MS = 200;
const SHUTDOWN_GRACE_MS = 2_000;
// frontend axios baseURL is configurable via VITE_API_BASE_URL; for e2e
// we pick a non-default port (18000) to avoid collision with dev / other
// projects on 8000, and inject the URL into the vite webServer via
// playwright.config.ts.
const E2E_BACKEND_PORT = Number(process.env.E2E_BACKEND_PORT ?? 18000);

async function isPortFree(port: number): Promise<boolean> {
  return new Promise((resolveP) => {
    const server = createServer();
    server.unref();
    server.once("error", () => resolveP(false));
    server.once("listening", () => {
      server.close(() => resolveP(true));
    });
    try {
      server.listen(port, "127.0.0.1");
    } catch {
      resolveP(false);
    }
  });
}

async function pollHealth(baseURL: string, child: ChildProcess): Promise<void> {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS;
  let lastError: unknown = null;

  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(
        `backend exited early with code ${child.exitCode} before becoming healthy`,
      );
    }
    try {
      const res = await fetch(`${baseURL}/health`);
      if (res.ok) {
        return;
      }
      lastError = new Error(`health responded ${res.status}`);
    } catch (err) {
      lastError = err;
    }
    await new Promise((r) => setTimeout(r, HEALTH_POLL_INTERVAL_MS));
  }

  throw new Error(
    `backend at ${baseURL} did not become healthy within ${HEALTH_TIMEOUT_MS}ms; last error: ${String(
      lastError,
    )}`,
  );
}

async function killGracefully(child: ChildProcess): Promise<void> {
  if (child.exitCode !== null) return;
  child.kill("SIGTERM");
  await new Promise<void>((r) => {
    const timer = setTimeout(() => {
      if (child.exitCode === null) {
        child.kill("SIGKILL");
      }
      r();
    }, SHUTDOWN_GRACE_MS);
    child.once("exit", () => {
      clearTimeout(timer);
      r();
    });
  });
}

export default async function globalSetup(): Promise<() => Promise<void>> {
  if (!existsSync(VENV_PYTHON)) {
    throw new Error(
      `backend venv python not found at ${VENV_PYTHON}; run 'uv venv backend/.venv --python 3.11 --seed' first`,
    );
  }

  const tmpRoot = mkdtempSync(join(tmpdir(), "coderecall-e2e-"));
  const dbPath = join(tmpRoot, "e2e.db");

  if (!(await isPortFree(E2E_BACKEND_PORT))) {
    rmSync(tmpRoot, { recursive: true, force: true });
    throw new Error(
      `Port ${E2E_BACKEND_PORT} is busy. Stop the dev backend (uvicorn) before running e2e tests; ` +
        `the frontend axios client (src/services/api.ts) hardcodes localhost:${E2E_BACKEND_PORT}.`,
    );
  }
  const port = E2E_BACKEND_PORT;
  // Use "localhost" (not 127.0.0.1) so e2e cookies share the same host as
  // playwright's page baseURL ("http://localhost:5173"). When backend is on a
  // different host (127.0.0.1), the SameSite cookie is technically cross-site
  // and chromium silently refuses to expose csrf_token to document.cookie in
  // the frontend origin — that breaks X-CSRF-Token injection by the axios
  // request interceptor.
  const baseURL = `http://localhost:${port}`;

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    DATABASE_URL: `sqlite:///${dbPath}`,
    JWT_SECRET_KEY: randomBytes(32).toString("hex"),
    OLD_USER_INITIAL_PASSWORD: "e2e-old-pass-1234",
    APP_ENV: "test",
    ENABLE_AI_ANALYSIS: "false",
    FRONTEND_ORIGIN: "http://localhost:5173",
    PYTHONUNBUFFERED: "1",
    // Disable rate-limiting in e2e so back-to-back register/login from many spec
    // workers doesn't get throttled.
    RATE_LIMIT_ENABLED: "false",
  };

  // 1. Run migrations synchronously before bringing up uvicorn.
  const migrate = spawnSync(
    VENV_PYTHON,
    ["-m", "alembic", "upgrade", "head"],
    { cwd: BACKEND_DIR, env, encoding: "utf-8" },
  );
  if (migrate.status !== 0) {
    rmSync(tmpRoot, { recursive: true, force: true });
    throw new Error(
      `alembic upgrade head failed (status ${migrate.status}):\n${migrate.stderr}`,
    );
  }

  // 2. Spawn uvicorn.
  const child = spawn(
    VENV_PYTHON,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(port),
      "--log-level",
      "warning",
    ],
    { cwd: BACKEND_DIR, env, stdio: ["ignore", "pipe", "pipe"] },
  );

  const stderrChunks: string[] = [];
  child.stdout?.on("data", () => {
    /* ignored — keep buffer small */
  });
  child.stderr?.on("data", (chunk: Buffer) => {
    const text = chunk.toString("utf-8");
    stderrChunks.push(text);
    if (stderrChunks.length > 200) stderrChunks.shift();
  });

  // 3. Wait until /health is up; tear down on timeout.
  try {
    await pollHealth(baseURL, child);
  } catch (err) {
    await killGracefully(child);
    rmSync(tmpRoot, { recursive: true, force: true });
    const tail = stderrChunks.slice(-50).join("");
    throw new Error(
      `${(err as Error).message}\n--- backend stderr (tail) ---\n${tail}`,
    );
  }

  process.env.E2E_BACKEND_URL = baseURL;

  // eslint-disable-next-line no-console
  console.log(`[e2e] backend ready at ${baseURL} (db=${dbPath})`);

  return async () => {
    try {
      await killGracefully(child);
    } finally {
      rmSync(tmpRoot, { recursive: true, force: true });
    }
  };
}
