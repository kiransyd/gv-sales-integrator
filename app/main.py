from __future__ import annotations

from fastapi import FastAPI

from app.logging import configure_logging
from app.settings import get_settings

from app.api.routes_debug import router as debug_router
from app.api.routes_health import router as health_router
from app.api.routes_webhooks_calendly import router as calendly_router
from app.api.routes_webhooks_readai import router as readai_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(title="GoVisually Integrations Service")
    app.include_router(health_router)
    app.include_router(calendly_router)
    app.include_router(readai_router)
    app.include_router(debug_router)
    return app


app = create_app()



