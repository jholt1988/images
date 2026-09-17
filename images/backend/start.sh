# Start uvicorn from this directory regardless of where the repo lives
cd "$(dirname "$0")"

if [ -f venv/bin/python ]; then
  exec venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 9119
elif [ -f ../backend/venv/bin/python ]; then
  exec ../backend/venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 9119
fi

exec python3 -m uvicorn app:app --host 0.0.0.0 --port 9119
