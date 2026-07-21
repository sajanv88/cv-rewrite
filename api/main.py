"""FastAPI application entry point for the CV Rewrite API.

Serves both the JSON API (under ``/api``, plus ``/health``) and the built React
SPA. In production the SPA lives in ``settings.static_dir`` and is served at
``/`` via ``app.frontend()`` so the two share one origin; in local dev that
directory is absent and the Vite dev server hosts the UI, proxying ``/api`` back
to this process.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.api.routers.coach import router as coach_router
from src.config.container import build_container
from src.infra.settings import Settings


def _inline_script_hashes(static_dir: str) -> list[str]:
    """CSP source-hashes for the SPA's inline bootstrap scripts.

    React Router (SPA mode) bakes a few small inline ``<script>`` blocks into
    index.html (the hydration context + module loader). Allowing them by their
    exact SHA-256 keeps ``script-src`` free of ``'unsafe-inline'`` — so arbitrary
    injected inline scripts stay blocked, which is the whole point of the CSP.
    Recomputed from the built file at startup, so it tracks each build.
    """
    index = os.path.join(static_dir, "index.html")
    if not os.path.isfile(index):
        return []
    with open(index, encoding="utf-8") as fh:
        html = fh.read()
    hashes: list[str] = []
    for content in re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE
    ):
        digest = hashlib.sha256(content.encode("utf-8")).digest()
        hashes.append("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
    return hashes


def _build_csp(script_hashes: list[str]) -> str:
    """Content Security Policy. Notable directives:

    - ``script-src 'self' <hashes>`` — no inline scripts except the SPA's own
      bootstrap (allowed by hash); the primary XSS defence.
    - ``style-src 'unsafe-inline'`` — Tailwind v4 injects styles at runtime.
    - ``connect-src`` — only same-origin (`/api/*`). Anthropic is listed for
      forward-compat; the browser talks to this server, which proxies to it.
    - ``frame-src data: blob:`` — the results PDF preview iframe uses a data: URI.
    - ``font-src / img-src 'self'`` — Inter is self-hosted; images are same-origin
      plus data:/blob: for generated PDFs.
    """
    script_src = " ".join(("'self'", *script_hashes))
    return "; ".join(
        (
            "default-src 'self'",
            f"script-src {script_src}",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self'",
            "connect-src 'self' https://api.anthropic.com",
            "frame-src 'self' data: blob:",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
        )
    )


settings = Settings()

_SECURITY_HEADERS = {
    "Content-Security-Policy": _build_csp(_inline_script_hashes(settings.static_dir)),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach CSP + hardening headers to every response (API and SPA alike)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers[name] = value
        return response


app = FastAPI(
    title="CV Rewrite API",
    description="Rewrite a CV against a job description — honestly — and score the fit.",
    version="0.1.0",
)
app.state.container = build_container(settings)

# Only needed when the SPA is served from a different origin (see settings).
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Registered after CORS so security headers are applied on the way out without
# disturbing the CORS headers. Wraps every route, including the SPA/static files.
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(coach_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Serve the built SPA at "/". FastAPI checks path operations (the API + /health)
# first and only falls back here if nothing matched, so the API is unaffected.
# `fallback="index.html"` handles client-side routing: HTML navigation requests
# for unknown paths get index.html, while missing JS/CSS/images still 404.
if os.path.isdir(settings.static_dir):
    app.frontend("/", directory=settings.static_dir, fallback="index.html")
