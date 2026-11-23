"""The web server: upload a test negative, render a preview, export."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "vendor" / "negpy"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
os.environ["DUMBCONVERT_DATA"] = tempfile.mkdtemp(prefix="dumbconvert-web-")

try:
    from fastapi.testclient import TestClient
except ImportError:                                   # fastapi / httpx are optional (requirements-web.txt)
    TestClient = None

import io  # noqa: E402

import numpy as np  # noqa: E402
import tifffile  # noqa: E402
from PIL import Image  # noqa: E402


def _negative(path: Path):
    """A small colour-negative-like TIFF: orange base, inverted gradient picture."""
    h, w = 400, 600
    y, x = np.mgrid[0:h, 0:w]
    scene = np.stack([x / w, y / h, 0.5 * np.ones((h, w))], axis=-1)
    neg = np.clip((1 - scene) * np.array([0.9, 0.6, 0.35]), 0, 1)
    neg[:12] = neg[-12:] = neg[:, :12] = neg[:, -12:] = (0.9, 0.6, 0.35)
    tifffile.imwrite(path, (neg * 65535).astype(np.uint16))


@unittest.skipIf(TestClient is None, "fastapi not installed")
class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from simpleneg.web import server
        cls.server = server
        with TestClient(server.app) as c:
            cls.tmp = Path(tempfile.mkdtemp())
            _negative(cls.tmp / "frame.tif")
            with (cls.tmp / "frame.tif").open("rb") as f:
                r = c.post("/api/photos", files=[("files", ("frame.tif", f, "image/tiff"))])
            assert r.status_code == 200, r.text
            cls.pid = r.json()[0]["id"]

    def test_info(self):
        with TestClient(self.server.app) as c:
            info = c.get("/api/info").json()
        self.assertIn("jpg", info["formats"])
        self.assertEqual(info["defaults"]["contrast"], 1.0)

    def test_preview_and_edit(self):
        with TestClient(self.server.app) as c:
            a = c.post(f"/api/photos/{self.pid}/preview", json={}, params={"long_edge": 400})
            b = c.post(f"/api/photos/{self.pid}/preview", json={"density": 1.3, "rotation": 1}, params={"long_edge": 400})
        self.assertEqual(a.status_code, 200, a.text)
        ia, ib = Image.open(io.BytesIO(a.content)), Image.open(io.BytesIO(b.content))
        self.assertEqual(ia.size[::-1], ib.size)                # a quarter turn swaps width and height
        self.assertNotEqual(a.content, b.content)

    def test_rejects_bad_input(self):
        with TestClient(self.server.app) as c:
            self.assertEqual(c.post(f"/api/photos/{self.pid}/preview", json={"contrast": "x"}).status_code, 400)
            self.assertEqual(c.post("/api/photos/nope/preview", json={}).status_code, 404)
            r = c.post("/api/photos", files=[("files", ("evil.exe", b"MZ", "application/octet-stream"))])
            self.assertEqual(r.status_code, 400)

    def test_export(self):
        with TestClient(self.server.app) as c:
            r = c.post(f"/api/photos/{self.pid}/export", json={"settings": {}, "format": "jpg", "long_edge": 300})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(max(Image.open(io.BytesIO(r.content)).size), 300)


if __name__ == "__main__":
    unittest.main()
