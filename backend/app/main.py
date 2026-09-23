import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .errors import NotFoundError, ValidationError
from .routers import activities, auth, contacts, deals, health, pipeline

app = FastAPI(
    title="Simple CRM API",
    version="1.0.0",
    servers=[{"url": "/api"}],
)

# In dev the frontend is served from a different origin than this API, so
# any origin is allowed by default. The Docker image serves both from one
# origin and sets SDIP_CORS_ORIGINS="" to turn CORS off; a comma-separated
# list allows just those origins.
CORS_ORIGINS = [o.strip() for o in os.environ.get("SDIP_CORS_ORIGINS", "*").split(",") if o.strip()]
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(ValidationError)
def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


api_router_modules = [pipeline, contacts, deals, activities, auth, health]
for module in api_router_modules:
    app.include_router(module.router, prefix="/api")

# In the Docker image the built frontend is served from the same origin as the
# API. Mounted last so the /api routes and /docs take precedence.
FRONTEND_DIR = os.environ.get("FRONTEND_DIR")
if FRONTEND_DIR:
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")
