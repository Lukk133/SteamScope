"""Fabryka aplikacji FastAPI dla SteamScope API."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_TITLE = "SteamScope API"
API_VERSION = "0.1.0"
API_DESCRIPTION = "REST API nad hurtownią analityczną Steam (warstwa wynikowa)."

# Domyślne adresy serwera deweloperskiego Vite — frontend Fazy 5.
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    """Tworzy nową instancję aplikacji FastAPI z zarejestrowanymi endpointami."""
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, str]:
        """Krótkie metadane aplikacji — odsyła do dokumentacji."""
        return {"name": API_TITLE, "docs": "/docs"}

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        """Endpoint zdrowia — używany przez monitoring i smoke-testy."""
        return {"status": "ok"}

    return app


# Eksport gotowej aplikacji dla `uvicorn backend.api.main:app`.
app = create_app()
