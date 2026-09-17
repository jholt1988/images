import os
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(BACKEND_DIR)

# Use a scratch dir so the test never touches real data/
scratch = tempfile.mkdtemp(prefix="images_test_")
os.chdir(scratch)

# backend.app uses bare-module imports (from vision_client import ...),
# so backend/ itself must be on sys.path, not the parent dir.
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402


def test_app_loads():
    from app import app
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    print("App loaded successfully, health:", data)


def test_upload_and_analyze_flow():
    """Smoke-test the core upload + get flow without a live VLM."""
    from app import app, db, vision_client
    from routes import api

    class FakeResult:
        def model_dump(self):
            return {
                "primary_type": "cat",
                "description": "A test cat",
                "tags": ["test", "cat"],
                "quality_score": 0.9,
            }

    async def fake_analyze(file_path):
        return FakeResult()

    original = vision_client.analyze_image
    api.vision_client.analyze_image = fake_analyze
    try:
        client = TestClient(app)
        import struct
        import zlib

        def tiny_png() -> bytes:
            sig = b"\x89PNG\r\n\x1a\n"
            def chunk(ctype, data):
                c = ctype + data
                return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
            iend = chunk(b"IEND", b"")
            return sig + ihdr + idat + iend

        png = tiny_png()
        r = client.post(
            "/api/v1/images/upload",
            files={"file": ("test.png", png, "image/png")},
        )
        assert r.status_code == 200, r.text
        image_id = r.json()["id"]
        assert r.json()["analyzed"] is True
        assert r.json()["analysis_error"] is None

        r2 = client.get(f"/api/v1/images/{image_id}")
        assert r2.status_code == 200
        detail = r2.json()
        assert detail["has_analysis"] == 1
        assert detail["analysis"]["primary_type"] == "cat"
        print("Upload + analyze OK, image_id:", image_id)

        r3 = client.delete(f"/api/v1/images/{image_id}")
        assert r3.status_code == 200
        print("Delete OK")
    finally:
        api.vision_client.analyze_image = original
