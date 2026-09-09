"""
RAXEL FastAPI Main Application Entry Point (Phase 7.1).
Connects REST API routers to existing RAXEL Python RAG & Governance backend.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.dependencies import ComponentRegistry
from backend.api import auth, chat, documents, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm RAXEL backend singletons on server startup."""
    ComponentRegistry.initialize()
    yield

app = FastAPI(
    title="RAXEL — AI-Powered College Knowledge Assistant API",
    description="REST API layer serving React frontend while preserving full RAG, vector store, SQLite auth, and governance intelligence.",
    version="7.0",
    lifespan=lifespan
)

# CORS Configuration for local React Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(admin.router)

@app.get("/api/health_check", tags=["Health"])
def api_health_check():
    """Simple API health check endpoint."""
    return {"status": "ok", "service": "RAXEL FastAPI Backend", "version": "7.0"}

# Static Files Serving for Production React Build (if compiled in frontend/dist)
dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return None
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
