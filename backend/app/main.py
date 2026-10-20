import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    admin,
    applications,
    auth,
    companies,
    evaluations,
    projects,
    recruiters,
    workspace,
)
from app.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    format_error_response,
    starlette_http_exception_handler,
    validation_error_handler,
)

app = FastAPI(
    title="ProjectProof AI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
origins = [
    settings.frontend_url,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


# Register standard error envelope handlers (docs/04-api-specification.md section 1)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    # Do not log personal info; return clean standard envelope
    return JSONResponse(
        status_code=500,
        content=format_error_response("server_error", "Internal server error", request_id, []),
    )


# Health check endpoint
@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}


# Mount API routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(recruiters.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")

