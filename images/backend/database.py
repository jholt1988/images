"""Database module for managing images and projects."""
import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
import uuid

class Database:
    """SQLite database for image analysis app."""
    
    def __init__(self, db_path: Optional[str] = None):
        # Anchor the default DB path to the repo root (backend/../data/images.db)
        # so the file lands in the same place no matter the working dir uvicorn
        # was started from.
        if db_path is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(repo_root, "data", "images.db")
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Images table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size INTEGER,
            file_hash TEXT,
            primary_type TEXT,
            description TEXT,
            tags TEXT,  -- JSON array
            quality_score REAL,
            has_analysis BOOLEAN DEFAULT 0,
            analysis_updated TIMESTAMP
        )
        ''')
        
        # Projects table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_images INTEGER DEFAULT 0,
            summary TEXT,
            metadata TEXT  -- JSON object
        )
        ''')
        
        # Image-Project relationships
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_projects (
            image_id TEXT,
            project_id TEXT,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_by TEXT,
            PRIMARY KEY (image_id, project_id),
            FOREIGN KEY (image_id) REFERENCES images(id),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        ''')
        
        # Analysis results table for detailed metadata
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id TEXT PRIMARY KEY,
            image_id TEXT NOT NULL,
            analysis_data TEXT NOT NULL,  -- JSON object
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (image_id) REFERENCES images(id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_image(self, file_path: str, filename: str) -> str:
        """Add a new image to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Generate unique ID
        image_id = uuid.uuid4().hex[:12]
        
        # Calculate file hash for deduplication
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Insert image record
        cursor.execute('''
        INSERT INTO images (id, filename, path, file_size, file_hash)
        VALUES (?, ?, ?, ?, ?)
        ''', (image_id, filename, file_path, file_size, file_hash))
        
        conn.commit()
        conn.close()
        
        return image_id
    
    def get_all_images(self, offset: int = 0, limit: int = 50) -> List[Dict]:
        """Get all images with pagination."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM images
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        images = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return images
    
    def get_total_images(self) -> int:
        """Get total count of images."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM images")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_image(self, image_id: str) -> Optional[Dict]:
        """Get a specific image by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        return dict(row) if row else None
    
    def delete_image(self, image_id: str):
        """Delete an image from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Remove from image-projects
        cursor.execute("DELETE FROM image_projects WHERE image_id = ?", (image_id,))
        
        # Remove analysis results
        cursor.execute("DELETE FROM analysis_results WHERE image_id = ?", (image_id,))
        
        # Delete image record
        cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
        
        conn.commit()
        conn.close()
    
    def update_image_metadata(self, image_id: str, metadata: Dict):
        """Update metadata for an image."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update fields based on metadata keys
        updates = []
        params = []
        
        for key, value in metadata.items():
            if key in ["primary_type", "description", "tags", "quality_score"]:
                updates.append(f"{key} = ?")
                params.append(json.dumps(value) if isinstance(value, (list, dict)) else value)
            elif key == "has_analysis":
                updates.append("has_analysis = 1")
                updates.append("analysis_updated = CURRENT_TIMESTAMP")
            elif key == "analysis_updated":
                # Already set by has_analysis, or use CURRENT_TIMESTAMP
                updates.append("analysis_updated = CURRENT_TIMESTAMP")
            elif key == "updated_at":
                updates.append("updated_at = CURRENT_TIMESTAMP")
        
        if updates:
            params.append(image_id)
            cursor.execute(
                f"UPDATE images SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
        
        conn.close()
    
    def index_image(self, image_id: str):
        """Index image file and extract metadata.

        Plain sync def: it only does blocking I/O (read + hash) with no awaits,
        so marking it async gained nothing and made callers write a spurious
        ``await`` on a coroutine that does no async work.
        """
        image = self.get_image(image_id)
        if not image:
            return
        
        # Extract basic metadata
        with open(image["path"], "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Update file hash
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE images SET file_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                      (file_hash, image_id))
        conn.commit()
        conn.close()
    
    def save_image_analysis(self, image_id: str, analysis_data: Dict):
        """Save image analysis results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create unique ID for analysis
        analysis_id = uuid.uuid4().hex[:12]
        
        # Save analysis
        cursor.execute('''
        INSERT INTO analysis_results (id, image_id, analysis_data)
        VALUES (?, ?, ?)
        ''', (analysis_id, image_id, json.dumps(analysis_data)))
        
        # Update image record with primary fields
        cursor.execute('''
        UPDATE images 
        SET 
            primary_type = ?,
            description = ?,
            tags = ?,
            quality_score = ?,
            has_analysis = 1,
            analysis_updated = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (
            analysis_data.get("primary_type"),
            analysis_data.get("description"),
            json.dumps(analysis_data.get("tags", [])),
            analysis_data.get("quality_score"),
            image_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_image_analysis(self, image_id: str) -> Optional[Dict]:
        """Get analysis results for an image."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT analysis_data FROM analysis_results WHERE image_id = ? ORDER BY created_at DESC LIMIT 1', 
                      (image_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return json.loads(row["analysis_data"])
        return None
    
    def find_hash_duplicates(self, threshold: float = 0.9) -> List[Dict]:
        """Find potential duplicates based on file hash similarity."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all images with hashes
        cursor.execute("SELECT id, filename, file_hash FROM images WHERE file_hash IS NOT NULL")
        image_hashes = [dict(row) for row in cursor.fetchall()]
        
        duplicates = []
        for i in range(len(image_hashes)):
            for j in range(i + 1, len(image_hashes)):
                hash1 = image_hashes[i]["file_hash"]
                hash2 = image_hashes[j]["file_hash"]
                
                # Calculate similarity (simple prefix match)
                similarity = self._calculate_hash_similarity(hash1, hash2)
                
                if similarity >= threshold:
                    duplicates.append({
                        "image1_id": image_hashes[i]["id"],
                        "image2_id": image_hashes[j]["id"],
                        "similarity": round(similarity, 3),
                        "reason": "Similar file hash"
                    })
        
        conn.close()
        return duplicates
    
    def _calculate_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two hashes."""
        if not hash1 or not hash2:
            return 0.0
        
        # Simple: compare first N characters
        common_prefix = sum(1 for a, b in zip(hash1, hash2) if a == b)
        return common_prefix / max(len(hash1), len(hash2))
    
    def get_similar_images(self, image_id: str, limit: int = 5) -> List[Dict]:
        """Get similar images based on tags and quality."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        current_image = self.get_image(image_id)
        if not current_image or not current_image.get("tags"):
            conn.close()
            return []
        
        current_tags = current_image["tags"]
        
        # Get similar images (excluding self)
        cursor.execute('''
        SELECT id, filename, primary_type, quality_score, tags
        FROM images 
        WHERE id != ? AND has_analysis = 1
        LIMIT ?
        ''', (image_id, limit))
        
        similar = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return similar
    
    def get_projects(self) -> List[Dict]:
        """Get all projects."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        projects = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return projects
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get a specific project by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        return dict(row) if row else None
    
    def create_project(self, name: str, description: str = "") -> Dict:
        """Create a new project."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        project_id = uuid.uuid4().hex[:12]
        
        cursor.execute('''
        INSERT INTO projects (id, name, description, metadata)
        VALUES (?, ?, ?, ?)
        ''', (
            project_id,
            name,
            description,
            json.dumps({"image_count": 0, "categories": [], "summary": ""})
        ))
        
        conn.commit()
        
        project = self.get_project(project_id)
        conn.close()
        
        return project
    
    def assign_image_to_project(self, image_id: str, project_id: str) -> bool:
        """Assign an image to a project."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if image exists
        cursor.execute("SELECT id FROM images WHERE id = ?", (image_id,))
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Check if project exists
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Add relationship (ignore duplicates)
        cursor.execute('''
        INSERT OR IGNORE INTO image_projects (image_id, project_id)
        VALUES (?, ?)
        ''', (image_id, project_id))
        
        # Update project image count
        cursor.execute('''
        UPDATE projects 
        SET total_images = (
            SELECT COUNT(*) FROM image_projects WHERE project_id = ?
        )
        WHERE id = ?
        ''', (project_id, project_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_project_images(self, project_id: str) -> List[Dict]:
        """Get all images in a project."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT i.*
        FROM images i
        JOIN image_projects ip ON i.id = ip.image_id
        WHERE ip.project_id = ?
        ORDER BY i.created_at DESC
        ''', (project_id,))
        
        images = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return images
    
    def get_project_analysis(self, project_id: str) -> Dict:
        """Get analysis metadata for a project."""
        images = self.get_project_images(project_id)
        
        # Aggregate analysis data
        all_tags = []
        total_files = len(images)
        analyzed_count = 0
        
        analysis_summary = {
            "total_files": total_files,
            "analyzed_files": analyzed_count,
            "all_tags": [],
            "category_counts": {},
            "description_suggestions": [],
            "tags_suggestions": [],
            "similar_projects": []
        }
        
        for image in images:
            if image["has_analysis"]:
                analyzed_count += 1
                
                # Collect tags
                if image["tags"]:
                    try:
                        tags = json.loads(image["tags"])
                        all_tags.extend(tags)
                        analysis_summary["all_tags"].extend(tags)
                    except json.JSONDecodeError:
                        pass
                
                # Collect categories
                if image["primary_type"]:
                    category = image["primary_type"]
                    analysis_summary["category_counts"][category] = \
                        analysis_summary["category_counts"].get(category, 0) + 1
        
        analysis_summary["analyzed_files"] = analyzed_count
        analysis_summary["description_suggestions"] = [img["description"] for img in images if img.get("description")]
        analysis_summary["tags_suggestions"] = list(set(all_tags))[:20]  # Unique tags, limit to 20
        
        return analysis_summary
    
    def update_project_metadata(self, project_id: str, metadata: Dict):
        """Update project metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current metadata
        cursor.execute("SELECT metadata FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        
        if row and row["metadata"]:
            current_metadata = json.loads(row["metadata"])
            current_metadata.update(metadata)
            
            cursor.execute('''
            UPDATE projects 
            SET metadata = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (json.dumps(current_metadata), project_id))
        else:
            cursor.execute('''
            UPDATE projects 
            SET metadata = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (json.dumps(metadata), project_id))
        
        conn.commit()
        conn.close()
    
    def close(self):
        """Close database connection."""
        # Database is auto-closed per connection in SQLite
        pass
