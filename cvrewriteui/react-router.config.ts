import type { Config } from "@react-router/dev/config";

export default {
  // SPA mode: no server render. `react-router build` emits a static client
  // bundle to build/client/; the `build` script then copies it into
  // ../api/static so FastAPI can serve it (see scripts/copy-to-api.mjs and
  // ../api/main.py). Note: React Router's SPA prerender must write inside the
  // project root, so we build here and copy, rather than building into ../api.
  ssr: false,
} satisfies Config;
