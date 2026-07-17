// Copies the built SPA (build/client) into the sibling API folder (api/static)
// so FastAPI serves it with no extra config — `static_dir` defaults to "static".
//
// Runs as the second half of `pnpm run build`. When there's no sibling api/ dir
// (e.g. the Docker web stage builds cvrewriteui alone), it's a no-op: the Docker
// image copies build/client into the image itself.

import { cpSync, existsSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const apiDir = resolve("..", "api");
const src = resolve("build", "client");
const dest = resolve(apiDir, "static");

if (!existsSync(apiDir)) {
  console.log(
    "[copy-to-api] no sibling ../api directory — skipping " +
      "(the Docker image copies build/client itself).",
  );
  process.exit(0);
}

if (!existsSync(src)) {
  console.error(`[copy-to-api] expected build output at ${src} — did the build run?`);
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
console.log("[copy-to-api] copied build/client -> api/static");
