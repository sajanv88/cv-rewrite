"""FastAPI application entry point for the CV Rewrite API.

Serves both the JSON API (under ``/api``, plus ``/health``) and the built React
SPA. In production the SPA lives in ``settings.static_dir`` and is served at
``/`` via ``app.frontend()`` so the two share one origin; in local dev that
directory is absent and the Vite dev server hosts the UI, proxying ``/api`` back
to this process.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.coach import router as coach_router
from src.config.container import build_container
from src.infra.settings import Settings

settings = Settings()

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
