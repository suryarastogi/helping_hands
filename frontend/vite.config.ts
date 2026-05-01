import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";

function tryGit(args: string): string | null {
  try {
    return execSync(`git ${args}`, { stdio: ["ignore", "pipe", "ignore"] })
      .toString()
      .trim();
  } catch {
    return null;
  }
}

function readNominalVersion(): string {
  try {
    const pkgPath = fileURLToPath(new URL("./package.json", import.meta.url));
    const pkg = JSON.parse(readFileSync(pkgPath, "utf-8")) as { version?: string };
    if (pkg.version) return pkg.version;
  } catch {
    // fall through
  }
  return "0.0.0";
}

function computeFrontendVersion(): {
  display: string;
  longSha: string;
  commitDate: string | null;
} {
  const nominal = readNominalVersion();
  const shortSha = tryGit("rev-parse --short HEAD");
  const longSha = tryGit("rev-parse HEAD");
  const porcelain = tryGit("status --porcelain");
  const commitDate = tryGit("log -1 --format=%cI");

  if (!shortSha || !longSha) {
    return { display: `${nominal}+unknown`, longSha: "unknown", commitDate: null };
  }
  const dirty = porcelain && porcelain.length > 0 ? "-dirty" : "";
  return {
    display: `${nominal}+${shortSha}${dirty}`,
    longSha,
    commitDate,
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

  const onProxyError = (err: Error) => {
    console.warn(`[vite] proxy error (non-fatal): ${err.message}`);
  };

  const apiProxy = {
    "/build": { target, changeOrigin: true },
    "/tasks": { target, changeOrigin: true },
    "/monitor": { target, changeOrigin: true },
    "/health": { target, changeOrigin: true },
    "/version": { target, changeOrigin: true },
    "/workers": { target, changeOrigin: true },
    "/config": { target, changeOrigin: true },
    "/schedules": { target, changeOrigin: true },
    "/grill": { target, changeOrigin: true },
    "/mgrill": { target, changeOrigin: true },
    "/arcade": { target, changeOrigin: true },
    "/repos": { target, changeOrigin: true },
  } as Record<string, object>;

  for (const key of Object.keys(apiProxy)) {
    (apiProxy[key] as Record<string, unknown>).configure = (
      proxy: { on: (event: string, handler: (...args: unknown[]) => void) => void },
    ) => {
      proxy.on("error", onProxyError);
    };
  }

  // Skip WS proxy in CI — no backend is running; e2e tests mock all routes.
  if (!process.env.CI) {
    apiProxy["/ws"] = {
      target,
      changeOrigin: true,
      ws: true,
      configure: (proxy: { on: (event: string, handler: (...args: unknown[]) => void) => void }) => {
        proxy.on("error", onProxyError);
      },
    };
  }

  const fe = computeFrontendVersion();

  return {
    server: { proxy: apiProxy },
    define: {
      __APP_VERSION__: JSON.stringify(fe.display),
      __APP_VERSION_LONG_SHA__: JSON.stringify(fe.longSha),
      __APP_VERSION_COMMIT_DATE__: JSON.stringify(fe.commitDate),
    },
  };
});
