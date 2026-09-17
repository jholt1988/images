"""Vision client for Ollama and OpenAI Vision."""
import os
import json
import base64
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import httpx
from database import Database

class ImageAnalysisResult(BaseModel):
    """Structured analysis result from vision model."""
    primary_type: str = Field(description="Main content category (e.g. 'landscape', 'portrait', 'screenshot')")
    description: str = Field(description="Detailed description of the image content")
    tags: List[str] = Field(default_factory=list, description="Relevant tags for categorization")
    estimated_size_categories: Dict[str, float] = Field(default_factory=dict, description="Confidence for image size categories")
    quality_score: float = Field(default=0.0, description="Image quality score 0-1")
    contains_text: bool = Field(default=False, description="Whether image contains significant text")
    text_content: str = Field(default="", description="Extracted text content if any")


class AnalysisError(Exception):
    """Raised when an image can't be analyzed — a transport/model failure
    (outage, timeout, non-200, missing response) or a reply that can't be
    parsed into the structured fields. Callers catch it so a failure is never
    saved behind has_analysis=1 as a best-effort 'unknown' placeholder."""


class VisionClient:
    """Client for vision language models."""
    
    def __init__(self):
        self.engine = os.getenv("VLM_ENGINE", "ollama")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "feadxus/Huihui-Qwen3-VL-4B-Instruct-abliterated:BF16")  # Use llava or qwen2-vl
        self.db = Database()
        self._available_models = None
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models."""
        available = {"ollama": [], "openai": []}
        
        # Check Ollama models if available
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.ollama_url.rstrip('/')}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    names = [m["name"] for m in models if m.get("name")]
                    # Report the configured model plus common vision models.
                    known = {"llava", "qwen2-vl"}
                    available["ollama"] = sorted(
                        {n for n in names if n.split(":")[0] in known or n == self.ollama_model}
                    )
        except Exception:
            available["ollama"] = []
        
        # Check OpenAI models
        if self.api_key:
            available["openai"].append(self.openai_model)
        
        return available
    
    async def analyze_image(self, file_path: str) -> ImageAnalysisResult:
        """Analyze an image file with vision model.

        Returns a populated ImageAnalysisResult on success. Raises AnalysisError
        on transport/model failure or when the reply can't be parsed into the
        structured fields — callers use that to decide whether to mark the image
        as analyzed, so a failure is never saved as a success.
        """
        try:
            if self.engine == "openai" and self.api_key:
                return await self._analyze_with_openai(file_path)
            return await self._analyze_with_ollama(file_path)
        except AnalysisError:
            raise
        except Exception as e:
            raise AnalysisError(f"Image analysis failed: {type(e).__name__}: {e}") from e
    
    async def _analyze_with_ollama(self, file_path: str) -> ImageAnalysisResult:
        """Analyze image using Ollama (llava or qwen2-vl)."""
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # System prompt for structured analysis - request explicit JSON
        system_prompt = '''You are an expert image analyst. Analyze the image and provide a JSON response with these exact fields:
- "primary_type": one word category (landscape, portrait, screenshot, document, photograph, drawing, icon, pattern, product, scene, etc)
- "description": one sentence description
- "tags": list of 2-3 relevant tags
- "estimated_size_categories": object with landscape/portrait/square as keys, all 0.0
- "quality_score": 0.75
- "contains_text": false
- "text_content": ""

Return ONLY a valid JSON object. Do not include markdown or extra text.'''
        
        url = f"{self.ollama_url}/api/chat"
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(url, json={
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Analyze this image and return JSON.", 
                     "images": [image_data]}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1024
                }
            })
            
            if response.status_code != 200:
                # The body is often empty on gateway failures (e.g. an expired
                # RunPod proxy returns 404 with no content), so include the
                # status code and the upstream headers to keep the message
                # diagnostic.
                detail = response.text or "(empty response body)"
                headers = {k: v for k, v in response.headers.items()
                           if k.lower().startswith(("x-", "server", "cf-"))}
                hint = ""
                if response.status_code == 404:
                    hint = " — check OLLAMA_URL: 404 usually means the Ollama server isn't reachable at that host/port (e.g. an expired RunPod proxy URL)."
                elif response.status_code in (401, 403):
                    hint = " — check OLLAMA_AUTH_TOKEN / auth headers."
                raise Exception(
                    f"Ollama API error: HTTP {response.status_code} {detail}"
                    + (f" [upstream headers: {headers}]" if headers else "")
                    + hint
                )
            
            result = response.json()
            content = result.get("message", {}).get("content", "")
            
            # Parse JSON response
            try:
                # Try to extract JSON from content (sometimes wrapped in markdown code blocks)
                clean_content = content.strip()
                
                # Remove markdown code blocks if present
                if clean_content.startswith("```"):
                    # Find the JSON within the code block
                    start_idx = clean_content.find("{", 3)
                    end_idx = clean_content.rfind("}") + 1
                    if start_idx > 0 and end_idx > start_idx:
                        clean_content = clean_content[start_idx:end_idx].strip()
                    else:
                        clean_content = clean_content[3:]
                        if clean_content.endswith("```"):
                            clean_content = clean_content[:-3]
                        clean_content = clean_content.strip()
                
                # If the content starts with a new line, skip it
                if clean_content.startswith("\n"):
                    clean_content = clean_content[1:]
                
                # Try to parse as JSON
                analysis_data = json.loads(clean_content)
                
                return ImageAnalysisResult(**analysis_data)
            except Exception as parse_error:
                snippet = (content or "")[:200]
                if isinstance(parse_error, json.JSONDecodeError):
                    print(f"Ollama response was not valid JSON: {parse_error}; raw: {snippet}")
                    raise AnalysisError(f"Ollama returned a non-JSON reply: {parse_error}; raw={snippet!r}") from parse_error
                # json parsed but fields were missing/invalid → not a real analysis.
                print(f"Ollama reply missing required fields: {parse_error}; raw: {snippet}")
                raise AnalysisError(f"Ollama reply was not a complete analysis; raw={snippet!r}") from parse_error
    
    async def _analyze_with_openai(self, file_path: str) -> ImageAnalysisResult:
        """Analyze image using OpenAI GPT-4o."""
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        system_prompt = """You are an expert image analyst. Analyze the image and provide:
1. primary_type: Main category
2. description: Detailed description
3. tags: list of tags
4. estimated_size_categories: confidence scores
5. quality_score: 0-1 estimate
6. contains_text: whether text is present
7. text_content: extracted text

Return your analysis as a JSON object."""
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", 
                 "content": [
                     {"type": "text", "text": "Analyze this image in detail"},
                     {"type": "image_url", 
                      "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                 ]}
            ],
            "max_tokens": 1000
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                detail = response.text or "(empty response body)"
                resp_headers = {k: v for k, v in response.headers.items()
                               if k.lower().startswith(("x-", "server", "cf-"))}
                hint = ""
                if response.status_code in (401, 403):
                    hint = " — check OPENAI_API_KEY."
                elif response.status_code == 404:
                    hint = " — check OPENAI_MODEL: 404 usually means the model name isn't valid for this key."
                raise Exception(
                    f"OpenAI API error: HTTP {response.status_code} {detail}"
                    + (f" [upstream headers: {resp_headers}]" if resp_headers else "")
                    + hint
                )
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                # Extract JSON from response
                if "```" in content:
                    json_str = content.split("```")[1].replace("json", "")
                else:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    json_str = content[start:end]
                
                analysis_data = json.loads(json_str)
                return ImageAnalysisResult(**analysis_data)
            except Exception as parse_error:
                snippet = (content or "")[:200]
                print(f"Failed to parse OpenAI response: {parse_error}; raw: {snippet}")
                raise AnalysisError(f"Could not parse OpenAI reply into a structured analysis; raw={snippet!r}") from parse_error
    
    async def find_similar_images(self, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find similar images using vision analysis."""
        images = self.db.get_all_images()
        similar_pairs = []
        
        # Analyze a sample of images for similarity
        sample_size = min(20, len(images))
        analyzed_images = []
        
        for i in range(sample_size):
            if images[i].get("has_analysis"):
                analyzed_images.append(images[i])
            else:
                try:
                    analysis = await self.analyze_image(images[i]["path"])
                except AnalysisError as e:
                    # A single un-analyzable image shouldn't sink the whole
                    # scan; skip it (it stays unanalyzed) and keep going.
                    print(f"Skipping image {images[i]['id']} in find_similar_images: {e}")
                    continue
                analysis_dict = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict()
                self.db.save_image_analysis(images[i]["id"], analysis_dict)
                # Store the analysis flat so the comparison loop below (which reads
                # .get("description")/.get("tags")) can actually see the fields.
                analyzed_images.append({
                    "id": images[i]["id"],
                    "filename": images[i].get("filename"),
                    **analysis_dict,
                })
        
        # Compare descriptions for similarity (simple text comparison)
        for i, img1 in enumerate(analyzed_images):
            for j, img2 in enumerate(analyzed_images[i+1:], i+1):
                # Calculate similarity score
                desc1 = img1.get("description", "") if isinstance(img1, dict) else img1.description
                desc2 = img2.get("description", "") if isinstance(img2, dict) else img2.description
                
                # Simple text similarity (could use embeddings for better results)
                similarity = self._calculate_text_similarity(desc1, desc2)
                
                if similarity >= threshold:
                    similar_pairs.append({
                        "image1_id": img1["id"],
                        "image2_id": img2["id"],
                        "similarity": round(similarity, 3),
                        "reason": "Similar visual content"
                    })
        
        return similar_pairs
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity score."""
        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    async def suggest_images_for_project(self, project_id: str, project_desc: str) -> List[Dict]:
        """Suggest best matching images for a project."""
        images = self.db.get_all_images(limit=50)
        suggestions = []
        
        for image in images:
            if image.get("has_analysis"):
                analysis = self.db.get_image_analysis(image["id"])
                desc = analysis.get("description", "")
                tags = analysis.get("tags", [])
            else:
                continue  # Skip unanalyzed images
            
            # Simple relevance scoring
            score = 0
            desc_lower = desc.lower()
            project_lower = project_desc.lower()
            
            # Match description keywords
            for word in project_lower.split():
                if len(word) > 3 and word in desc_lower:
                    score += 2
                if word in desc:
                    score += 1
            
            # Match tags
            for tag in tags:
                tag_lower = tag.lower()
                for word in project_lower.split():
                    if word in tag_lower:
                        score += 3
            
            if score > 0:
                suggestions.append({
                    "id": image["id"],
                    "filename": image["filename"],
                    "path": image["path"],
                    "score": score,
                    "matching_tags": [t for t in tags if any(w.lower() in t.lower() for w in project_lower.split())]
                })
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:10]
    
    def generate_project_summary(self, analysis_data: Dict) -> str:
        """Generate a natural language summary of a project."""
        images = analysis_data.get("images", [])
        if not images:
            return "No images analyzed yet."
        
        # Simple summary generation based on analysis
        tags = []
        for img in images:
            if isinstance(img, dict) and "analysis" in img:
                tags.extend(img.get("analysis", {}).get("tags", []))
            elif hasattr(img, "tags"):
                tags.extend(img.tags)
        
        # Get most common tags
        tag_counts = {}
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        summary = f"This project contains {len(images)} image(s). "
        if common_tags:
            summary += "Main content types include: " + ", ".join([t[0] for t in common_tags])
        return summary
