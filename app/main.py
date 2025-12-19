from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.logging import configure_logging
from app.settings import get_settings

from app.api.routes_debug import router as debug_router
from app.api.routes_enrich import router as enrich_router
from app.api.routes_health import router as health_router
from app.api.routes_webhooks_calendly import router as calendly_router
from app.api.routes_webhooks_intercom import router as intercom_router
from app.api.routes_webhooks_readai import router as readai_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    # Validate configuration and fail fast if critical errors found
    settings.validate_and_fail_fast()

    app = FastAPI(
        title="GoVisually Integrations Service",
        docs_url="/docs",  # Swagger UI (default, works reliably)
        redoc_url=None,  # Disable default ReDoc (CDN issue), we'll use custom route
        openapi_url="/openapi.json",
    )
    
    # Custom ReDoc route with working CDN URL
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> HTMLResponse:
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>GoVisually Integrations Service - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
      body {
        margin: 0;
        padding: 0;
      }
    </style>
</head>
<body>
    <noscript>
        ReDoc requires Javascript to function. Please enable it to browse the documentation.
    </noscript>
    <redoc spec-url="/openapi.json"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"></script>
</body>
</html>
        """
        return HTMLResponse(content=html)
    
    app.include_router(health_router)
    app.include_router(calendly_router)
    app.include_router(readai_router)
    app.include_router(intercom_router)
    app.include_router(enrich_router)
    app.include_router(debug_router)
    return app


app = create_app()



