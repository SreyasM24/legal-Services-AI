"""
AXIOM — AI-Powered Legal Document Analysis and Information Retrieval
FastAPI Main Application Entry Point
"""

import sys
from pathlib import Path

# Ensure 'app' is importable regardless of whether execution starts from project root or /backend
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
for d in (str(current_dir), str(backend_dir)):
    if d not in sys.path:
        sys.path.insert(0, d)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.services.extractor import ExtractionError


app = FastAPI(
    title="AXIOM — Legal Document Analysis & Retrieval API",
    description=(
        "AI-Powered Legal Document Analysis and Information Retrieval platform. "
        "Extracts, summarizes, detects clauses, and performs passage search using "
        "TF-IDF, Cosine Similarity, and rule-based NLP."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ExtractionError)
async def extraction_error_handler(request: Request, exc: ExtractionError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_type": "ExtractionError"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # Hide internal server paths or sensitive details from client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing the request.",
            "error_type": "InternalServerError",
        },
    )


# 1. Register API routes first so /api/* and /docs are never shadowed
app.include_router(api_router)


# 2. Locate frontend directory using absolute path
project_root = backend_dir.parent
frontend_dir = project_root / "frontend"


# 3. Mount static assets (CSS, JS)
if (frontend_dir / "css").is_dir():
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")

if (frontend_dir / "js").is_dir():
    app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")


# 4. Serve single-page application at / and /index.html
@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = frontend_dir / "index.html"
    if index_file.is_file():
        return FileResponse(str(index_file))
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend index.html was not found on the server."},
    )


@app.get("/index.html", include_in_schema=False)
async def serve_index_html():
    index_file = frontend_dir / "index.html"
    if index_file.is_file():
        return FileResponse(str(index_file))
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend index.html was not found on the server."},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
