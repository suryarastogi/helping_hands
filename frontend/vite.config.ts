import { defineConfig, loadEnv } from "vite";

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

  return { server: { proxy: apiProxy } };
});
