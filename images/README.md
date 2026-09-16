# Image Analysis App

A web application that uses Vision Language Models (VLM) to analyze images, detect duplicates, mark for deletion, and compile images into projects.

## ✨ Features

- **Image Analysis**: Analyze images using Ollama (llava) or OpenAI GPT-4o Vision API
- **Duplicate Detection**: Find similar images by hash and visual similarity
- **Project Organization**: Create projects and assign images based on content analysis
- **Suggestion Engine**: Get automatic project suggestions based on image analysis
- **Compile & Export**: Generate markdown reports or JSON for projects

## 🏗️ Architecture

```
backend/
├── app.py              # FastAPI application entry point
├── vision_client.py    # VLM integration (Ollama + OpenAI)
├── database.py         # SQLite database operations
├── models/             # Pydantic models
└── routes/
    └── api.py          # API route handlers

frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/          # Page components
│   └── services/       # API service layer
└── package.json

data/
├── images/
│   ├── originals/      # Uploaded images
│   └── duplicates/     # Detected duplicates
├── projects/           # Project exports
└── images.db           # SQLite database
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Ollama (for local VLM) with `llava` model
- OR OpenAI API key (for GPT-4o Vision)

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run FastAPI server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup (optional)

```bash
cd frontend
npm install
npm run dev
```

## 📋 API Endpoints

### Health & Configuration
- `GET /api/v1/health` - Check service status and available models

### Image Management
- `POST /api/v1/images/upload` - Upload single image
- `POST /api/v1/images/upload/batch` - Batch upload images
- `GET /api/v1/images/all?page=1&limit=50` - List images (paginated)
- `GET /api/v1/images/{image_id}` - Get image details
- `DELETE /api/v1/images/{image_id}` - Delete/soft-delete image

### Analysis
- `POST /api/v1/images/{image_id}/analyze` - Analyze image with VLM
- `POST /api/v1/images/analyze/batch` - Batch analyze multiple images
- `GET /api/v1/analysis/duplicates?threshold=0.8` - Find image duplicates

### Projects
- `GET /api/v1/projects` - List all projects
- `POST /api/v1/projects` - Create new project
- `POST /api/v1/projects/{project_id}/assign` - Assign images to project
- `GET /api/v1/projects/{project_id}/suggestions` - Get project suggestions
- `POST /api/v1/compile?format=json|markdown` - Compile project

## 🔧 Configuration

Create a `.env` file in the backend directory:

```env
# Vision Model Engine: 'ollama' or 'openai'
VLM_ENGINE=ollama

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava

# OpenAI Configuration
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o
```

## 📊 Analysis Output

The VLM returns structured analysis:

```json
{
  "primary_type": "landscape",
  "description": "Detailed description of image content...",
  "tags": ["nature", "mountains", "sunset"],
  "quality_score": 0.85,
  "contains_text": false,
  "estimated_size_categories": {
    "landscape": 0.95,
    "portrait": 0.03,
    "square": 0.02
  }
}
```

## 🗄️ Database

Uses SQLite for simplicity. Schema includes:
- `images`: Core image metadata
- `projects`: Project definitions
- `image_projects`: Junction table for assignments
- `analysis_results`: Detailed VLM analysis

## 🚀 Deployment

### Docker (recommended)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/

# Install Ollama if using local VLM
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://ollama.ai/install.sh | sh

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Service
```ini
[Unit]
Description=Image Analysis App
After=network.target

[Service]
Type=simple
User=ollama
WorkingDirectory=/opt/image-analyzer
ExecStart=/opt/image-analyzer/backend/venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 🔒 Security Considerations

- Validate file types on upload
- Limit file sizes (default: 10MB)
- Sanitize filenames
- Use HTTPS in production
- Rate limit API endpoints

## 📈 Performance Tips

- Enable Redis caching for repeated analyses
- Use async image processing for large batches
- Implement CDN for static assets
- Add database indexes for complex queries

## 🧪 Testing

```bash
cd backend
python -m pytest tests/ --cov=backend --cov-report=html
```

## 📝 License

MIT License

## 👥 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

Built with ❤️ using FastAPI, React, and Vision Language Models
