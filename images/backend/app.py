"""FastAPI application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from vision_client import VisionClient
from routes import api

# Initialize application
# Port 9119 configured
app = FastAPI(
    title="Image Analysis App",
    description="Vision-based image analysis with deduplication and project organization",
    version="1.0.0"
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

# Initialize vision client
vision_client = VisionClient()
print(f"Vision engine: {vision_client.engine}")
print(f"Available models: {vision_client.get_available_models()}")

# Include API routes
app.include_router(api.router, prefix="/api/v1", tags=["api"])

# Serve frontend if available
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")

# Create necessary directories
os.makedirs("data/images/originals", exist_ok=True)
os.makedirs("data/images/duplicates", exist_ok=True)
os.makedirs("data/projects", exist_ok=True)
os.makedirs("logs", exist_ok=True)

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
        "engine": vision_client.engine,
        "models": vision_client.get_available_models()
    }
