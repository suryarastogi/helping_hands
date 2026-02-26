import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    server: {
      proxy: {
        "/build": {
          target,
          changeOrigin: true,
        },
        "/tasks": {
          target,
          changeOrigin: true,
        },
        "/monitor": {
          target,
          changeOrigin: true,
        },
        "/health": {
          target,
          changeOrigin: true,
        },
      },
    },
  };
});
