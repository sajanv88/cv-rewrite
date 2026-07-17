import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, type Plugin } from "vite";

// Chrome DevTools probes `/.well-known/appspecific/com.chrome.devtools.json` on
// every page load; without a handler the dev server logs "No route matches".
// Answer it with 204 so the dev terminal stays clean. Dev-only — production is
// served by FastAPI, which simply 404s the probe (no log spam there).
function silenceDevToolsProbe(): Plugin {
  return {
    name: "silence-devtools-probe",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(
        "/.well-known/appspecific/com.chrome.devtools.json",
        (_req, res) => {
          res.statusCode = 204;
          res.end();
        },
      );
    },
  };
}

// In production the API and this SPA share one origin (FastAPI serves the built
// bundle), so the app uses relative URLs like `/api/rewrite`. During `dev`, the
// Vite server proxies those same paths to the FastAPI dev server on :8000 — so
// there's no CORS to configure and no API URL to bake in.
export default defineConfig({
  plugins: [tailwindcss(), reactRouter(), silenceDevToolsProbe()],
  resolve: {
    tsconfigPaths: true,
  },
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
