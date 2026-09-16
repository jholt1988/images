# Start uvicorn from correct working directory
cd /workspace/projects/images
/workspace/projects/images/backend/venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 9119
