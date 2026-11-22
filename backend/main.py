"""The UnderCover backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend import database
from backend.records import NotFound
from backend.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the database on first start."""
    app.state.database_path = database.path_from_environment()
    database.prepare(app.state.database_path)
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(NotFound)
def not_found(request: Request, error: NotFound) -> JSONResponse:
    """Answer 404 with the reason."""
    return JSONResponse({"detail": str(error)}, status_code=404)


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}
