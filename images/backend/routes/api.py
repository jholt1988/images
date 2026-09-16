"""Main API routes for the image analysis application."""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Body
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import sqlite3
import json
from datetime import datetime
import httpx

from vision_client import VisionClient, ImageAnalysisResult
from database import Database

router = APIRouter()

# Initialize dependencies
vision_client = VisionClient()
db = Database()

# Stored image "path" values are root-relative; these anchor resolution and
# the containment check for the preview endpoint below.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGES_DATA_DIR = (PROJECT_ROOT / "data" / "images").resolve()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "engine": os.getenv("VLM_ENGINE", "ollama"),
        "models": vision_client.get_available_models()
    }


@router.get("/models")
async def list_vision_models():
    """List available vision models for the selected engine."""
    engine = os.getenv("VLM_ENGINE", "ollama")
    if engine == "ollama":
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{os.getenv('OLLAMA_URL', 'https://b9y9yyr9f6j4h0-11434.proxy.runpod.net')}/api/tags"
                )
                if response.status_code == 200:
                    models_data = response.json().get("models", [])
                    vision_models = []
                    for m in models_data:
                        caps = m.get("capabilities", [])
                        name = m.get("name", "").split(":")[0]
                        full_name = m.get("name", "")
                        size_mb = round(m.get("size", 0) / (1024 * 1024))
                        vision_models.append({
                            "name": name,
                            "full_name": full_name,
                            "size_mb": size_mb,
                            "capabilities": caps,
                            "is_vision": "vision" in caps,
                            "engine": "ollama"
                        })
                    return {"models": vision_models, "engine": "ollama"}
                return {"models": [], "engine": "ollama", "error": "Bad response"}
        except Exception as e:
            return {"models": [], "engine": "ollama", "error": str(e)}
    elif engine == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            return {
                "models": [{"name": os.getenv("OPENAI_MODEL", "gpt-4o-vision"), "engine": "openai"}],
                "engine": "openai"
            }
        return {"models": [], "engine": "openai", "error": "No API key"}
    return {"models": [], "engine": "unknown"}


# ==================== Settings ====================

# Masked placeholder returned by GET /settings for the OpenAI API key. The
# frontend echoes this value back on save; the save endpoint treats the exact
# sentinel as "no change" so a UI round-trip never clobbers the real key with
# the sentinel. An empty string explicitly clears the key.
OPENAI_KEY_SENTINEL = "***"


def _settings_file() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "app_settings.json")


def _load_settings() -> Dict:
    """Read the settings file, tolerating absence/corruption. Enforces 0600
    because the file can hold secrets."""
    path = _settings_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            settings = json.load(f)
        if isinstance(settings, dict):
            os.chmod(path, 0o600)
            return settings
    except (json.JSONDecodeError, OSError):
        pass
    return {}


@router.get("/settings")
async def get_settings():
    """Read persisted app settings with the OpenAI API key masked so the raw
    secret is never sent to browsers (devtools, history, service workers…)."""
    settings = _load_settings()
    if settings.get("OPENAI_API_KEY"):
        settings["OPENAI_API_KEY"] = OPENAI_KEY_SENTINEL
    return settings


@router.post("/settings")
async def save_settings(data: dict):
    """Persist app settings to the config file (0600; key handled via sentinel)."""
    # Validate settings keys
    valid_keys = {'VLM_ENGINE', 'OLLAMA_URL', 'OLLAMA_MODEL', 'OPENAI_API_KEY', 'OPENAI_MODEL', 'UPLOAD_MAX_SIZE'}
    invalid_keys = set(data.keys()) - valid_keys
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid settings keys: {invalid_keys}")

    # Validate VLM_ENGINE
    if "VLM_ENGINE" in data and data["VLM_ENGINE"] not in ("ollama", "openai"):
        raise HTTPException(status_code=400, detail="VLM_ENGINE must be 'ollama' or 'openai'")

    # The mask echo from the UI means "keep the existing key"; drop it so the
    # merged result falls back to whatever is already stored.
    if data.get("OPENAI_API_KEY") == OPENAI_KEY_SENTINEL:
        data = {k: v for k, v in data.items() if k != "OPENAI_API_KEY"}

    # Merge with previously saved settings so partial saves don't clobber other keys
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    settings_path = os.path.join(config_dir, "app_settings.json")
    merged = _load_settings()
    merged.update(data)

    try:
        os.makedirs(config_dir, exist_ok=True)

        with open(settings_path, "w") as f:
            json.dump(merged, f, indent=2)
        # Settings can hold secrets; keep the file owner-only.
        os.chmod(settings_path, 0o600)

        # Apply new config to environment and rebuild the shared VisionClient
        # (it reads all config in __init__, so a fresh instance picks changes up
        # without a process restart)
        for key, value in merged.items():
            if key == "UPLOAD_MAX_SIZE":
                continue
            os.environ[key] = str(value)

        global vision_client
        new_client = VisionClient()
        vision_client = new_client
        # Update the client's own db handle so both share state
        new_client.db = db

        return {"status": "ok", "message": "Settings saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Image Management ====================

@router.post("/images/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload a single image for analysis."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    
    # Check file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File size must be less than 10MB")
    
    # Save file
    images_dir = Path("data/images/originals")
    images_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    filepath = images_dir / filename
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Add to database
    image_id = db.add_image(str(filepath), file.filename)
    await db.index_image(image_id)
    
    # Automatically analyze the uploaded image (run in background via async)
    analyzed = False
    analysis_error = None
    try:
        analysis = await vision_client.analyze_image(str(filepath))
        db.save_image_analysis(image_id, analysis.dict())
        db.update_image_metadata(image_id, {
            "has_analysis": True,
            "analysis_updated": datetime.now().isoformat()
        })
        analyzed = True
    except Exception as e:
        # The upload itself succeeded; only the auto-analysis failed. Report
        # that honestly instead of marking an un-analyzable image as analyzed.
        print(f"Auto-analysis failed for {file.filename}: {e}")
        analysis_error = str(e)
    
    return {
        "id": image_id,
        "filename": file.filename,
        "path": str(filepath),
        "analyzed": analyzed,
        "analysis_error": analysis_error,
    }


@router.post("/images/upload/batch")
async def upload_images(files: List[UploadFile] = File(...)):
    """Upload multiple images."""
    uploaded = []
    
    for file in files:
        if file.content_type and file.content_type.startswith("image/"):
            result = await upload_image(file)
            uploaded.append(result)
    
    return {"uploaded": uploaded, "count": len(uploaded)}


@router.get("/images/all")
async def get_all_images(page: int = 1, limit: int = 50):
    """Get all images with pagination."""
    start = (page - 1) * limit
    end = start + limit
    
    images = db.get_all_images(start, limit)
    total = db.get_total_images()
    
    return {
        "images": images,
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": end < total
    }


@router.get("/images/file/{image_id}")
async def serve_image(image_id: str):
    """Serve the original image file for a stored image so the UI can preview it.

    The image's `path` is persisted relative to the project root. We resolve it,
    confirm the result stays under the image-storage directory (defense in depth
    against path traversal, even though the path is server-authored), and stream
    it back with the correct content type for inline rendering in <img>.
    """
    image = db.get_image(image_id)
    if not image or not image.get("path"):
        raise HTTPException(404, "Image not found")

    stored = image["path"]
    candidate = Path(stored) if os.path.isabs(stored) else (PROJECT_ROOT / stored)
    candidate = candidate.resolve()

    try:
        candidate.relative_to(IMAGES_DATA_DIR)
    except ValueError:
        raise HTTPException(404, "Image not found")

    if not candidate.is_file():
        raise HTTPException(404, "Image file not found on disk")

    # No `filename=` on FileResponse: that sets Content-Disposition: attachment,
    # which makes the browser download instead of render. Omitting it leaves the
    # response inline so it displays directly in the <img> tag.
    return FileResponse(candidate)


@router.get("/images/{image_id}")
async def get_image_details(image_id: str):
    """Get details of a specific image."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    
    # Return analysis if available
    analysis = db.get_image_analysis(image_id)
    image["analysis"] = analysis
    
    # Find similar images
    similar = db.get_similar_images(image_id)
    image["similar"] = similar
    
    return image


@router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    """Delete an image or mark for deletion."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    
    # Move to trash (anchored to repo root, independent of CWD)
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    trash_dir = PROJECT_ROOT / "data" / "images" / "trash"
    trash_dir.mkdir(parents=True, exist_ok=True)

    if image["path"].endswith((".txt", ".json")):
        # Skip metadata files
        return {"id": image_id, "deleted": False, "reason": "metadata"}

    dest_path = trash_dir / image["filename"]
    # Handle filename collisions in trash by appending a counter
    candidate = dest_path
    counter = 1
    while candidate.exists():
        stem = Path(image["filename"]).stem
        suffix = Path(image["filename"]).suffix
        candidate = trash_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    dest_path = candidate

    os.rename(image["path"], str(dest_path))
    db.delete_image(image_id)

    return {"id": image_id, "deleted": True, "path": str(dest_path)}


# ==================== Analysis ====================

@router.post("/images/{image_id}/analyze")
async def analyze_image(image_id: str, force: bool = False):
    """Analyze an image with vision model."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    
    if not force and image.get("has_analysis"):
        # Return existing analysis
        analysis = db.get_image_analysis(image_id)
        return {
            "image_id": image_id,
            "analysis": analysis,
            "fresh": False
        }
    
    try:
        # Run analysis
        result = await vision_client.analyze_image(image["path"])
        
        # Save analysis
        db.save_image_analysis(image_id, result.dict())
        db.update_image_metadata(image_id, {
            "has_analysis": True,
            "analysis_updated": datetime.now().isoformat()
        })
        
        # Find similar images
        similar = db.get_similar_images(image_id)
        
        return {
            "image_id": image_id,
            "analysis": result,
            "similar": similar[:5]  # Limit similar results
        }
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/images/analyze/batch")
async def batch_analyze_images(image_ids: List[str]):
    """Analyze multiple images in batch."""
    results = {}
    
    for image_id in image_ids:
        try:
            result = await analyze_image(image_id, force=True)
            results[image_id] = result.get("analysis")
        except Exception as e:
            results[image_id] = {"error": str(e)}
    
    return {"results": results}


# ==================== Deduplication ====================

@router.get("/analysis/duplicates")
async def find_duplicates(threshold: float = 0.8):
    """Find duplicate images using multiple methods."""
    # Method 1: Hash-based
    hash_duplicates = db.find_hash_duplicates(threshold)
    
    # Method 2: VLM-based
    vlm_duplicates = await vision_client.find_similar_images(threshold)
    
    # Combine results
    duplicates = hash_duplicates + [
        d for d in vlm_duplicates 
        if d["image1_id"] not in [h["image1_id"] for h in hash_duplicates]
    ][:100]  # Limit results
    
    return {
        "duplicates": duplicates,
        "total_hash_matches": len(hash_duplicates),
        "total_vlm_matches": len(vlm_duplicates),
        "threshold": threshold
    }


# ==================== Project Management ====================

@router.get("/projects")
async def get_projects():
    """Get all projects."""
    projects = db.get_projects()
    return {
        "projects": [{
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "image_count": len(p.get("images", [])),
            "created_at": p["created_at"],
            "summary": p.get("summary", "No summary available")
        } for p in projects]
    }


@router.post("/projects")
async def create_project(project_data: dict):
    """Create a new project."""
    name = project_data.get("name", "")
    description = project_data.get("description", "")
    project = db.create_project(name, description)
    
    # Auto-suggest images for the project based on description
    suggestions = await vision_client.suggest_images_for_project(
        project["id"], description
    )
    
    return {
        "project": project,
        "suggested_images": suggestions
    }


@router.post("/projects/{project_id}/assign")
async def assign_images_to_project(
    project_id: str,
    image_ids: List[str],
    auto_assign: bool = False
):
    """Assign images to a project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    assigned = []
    for image_id in image_ids:
        if db.assign_image_to_project(image_id, project_id):
            assigned.append(image_id)
    
    return {
        "project_id": project_id,
        "assigned": len(assigned),
        "images": assigned
    }


@router.get("/projects/{project_id}/suggestions")
async def get_project_suggestions(project_id: str):
    """Get suggestions for a project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get analysis metadata from images
    analysis = db.get_project_analysis(project_id)
    
    suggestions = {
        "description_suggestions": analysis.get("description_suggestions", []),
        "tags_suggestions": analysis.get("tags_suggestions", []),
        "similar_projects": analysis.get("similar_projects", [])
    }
    
    # Generate project summary if needed
    if not project.get("summary"):
        summary = vision_client.generate_project_summary(analysis)
        db.update_project_metadata(project_id, {"summary": summary})
    else:
        summary = project["summary"]
    
    return {
        "project_id": project_id,
        "suggestions": suggestions,
        "summary": summary
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and its image relationships."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Remove image-project relationships
    cursor = sqlite3.connect(db.db_path).cursor()
    cursor.execute("DELETE FROM image_projects WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    cursor.connection.commit()
    cursor.connection.close()
    
    return {"project_id": project_id, "deleted": True, "message": "Project deleted"}


# ==================== Compile ====================

@router.post("/compile")
async def compile_project(project_id: str = Body(...), output_format: str = "json"):
    """Compile project into specified format."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get all images and analyses
    project_data = {
        "project": project,
        "images": db.get_project_images(project_id),
        "analysis": db.get_project_analysis(project_id)
    }
    
    # Compile in requested format
    if output_format == "json":
        return project_data
    elif output_format == "markdown":
        # Generate markdown report
        md = f"# {project['name']}\n\n"
        md += f"{project.get('description', '')}\n\n"
        md += "## Images\n\n"
        for img in project_data["images"]:
            analysis = db.get_image_analysis(img["id"])
            md += f"### {img['filename']}\n\n"
            md += f"- Type: {analysis.get('primary_type', 'Unknown')}\n"
            md += f"- Tags: {', '.join(analysis.get('tags', [])[:5])}\n\n"
        return {"content": md, "format": "markdown"}
    else:
        raise HTTPException(400, f"Unsupported format: {output_format}")


# ==================== Database Initialization ====================

@router.post("/db/init")
async def init_database():
    """Initialize database if not already done."""
    db.init_database()
    return {"status": "initialized", "database": "images.db"}
