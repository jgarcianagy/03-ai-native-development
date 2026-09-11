from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from .errors import NotFoundError, ValidationError
from .routers import activities, auth, contacts, deals, pipeline

app = FastAPI(
    title="Simple CRM API",
    version="1.0.0",
    servers=[{"url": "/api"}],
)

# Dev-only: the frontend is served from a different origin than this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(ValidationError)
def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


api_router_modules = [pipeline, contacts, deals, activities, auth]
for module in api_router_modules:
    app.include_router(module.router, prefix="/api")
