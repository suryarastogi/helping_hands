import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

  const apiProxy = {
    "/build": { target, changeOrigin: true },
    "/tasks": { target, changeOrigin: true },
    "/monitor": { target, changeOrigin: true },
    "/health": { target, changeOrigin: true },
    "/workers": { target, changeOrigin: true },
    "/config": { target, changeOrigin: true },
    "/schedules": { target, changeOrigin: true },
    "/arcade": { target, changeOrigin: true },
  } as Record<string, object>;

  // Skip WS proxy in CI — no backend is running; e2e tests mock all routes.
  if (!process.env.CI) {
    apiProxy["/ws"] = { target, changeOrigin: true, ws: true };
  }

  return { server: { proxy: apiProxy } };
});
