import sys, os
sys.path.insert(0, "/workspace/projects/images/backend")
os.chdir("/workspace/projects/images")

from backend.app import app
print("App loaded successfully")
