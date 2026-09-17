"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from vision_client import VisionClient
from routes import api
from database import Database

db = Database()

# Anchor runtime directories to the repo root so they resolve the same way
# regardless of the CWD the server is started from.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _project_data_dir(*parts: str) -> str:
    return os.path.join(APP_ROOT, *parts)


# Initialize application
vision_client = VisionClient()

# Point the API router at this process's shared vision client + database so a
# settings save (which swaps the router's vision_client) can't leave two
# clients out of sync.
api.vision_client = vision_client
api.db = db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create necessary directories
    os.makedirs(_project_data_dir("data", "images", "originals"), exist_ok=True)
    os.makedirs(_project_data_dir("data", "images", "duplicates"), exist_ok=True)
    os.makedirs(_project_data_dir("data", "projects"), exist_ok=True)
    os.makedirs(_project_data_dir("logs"), exist_ok=True)
    # Automatically initialize the database tables when the server starts.
    db.init_database()
    print("Database initialized successfully on startup.")
    yield


app = FastAPI(
    title="Image Analysis App",
    description="Vision-based image analysis with deduplication and project organization",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
# allow_credentials=True is incompatible with allow_origins=["*"] per the CORS
# spec (browsers reject credentialed cross-origin requests in that combo).
# Set credentials to False so the wildcard origin actually works; tighten both
# to concrete origins if you add authentication cookies later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"Vision engine: {vision_client.engine}")
print(f"Available models: {vision_client.get_available_models()}")

# Include API routes
app.include_router(api.router, prefix="/api/v1", tags=["api"])

# Serve frontend if available
frontend_dist_path = os.path.join(APP_ROOT, "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Image Analysis App",
        "version": "1.0.0",
        "docs": "/api/v1/docs",
        "health": "/api/v1/health"
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "engine": api.vision_client.engine,
        "models": api.vision_client.get_available_models()
    }