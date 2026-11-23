"""A small web server around simpleneg.engine, so DumbConvert can be used from Safari on an iPad.

    python -m simpleneg.web --host 0.0.0.0 --port 8000

Your scans stay on the machine that runs this server. Set DUMBCONVERT_TOKEN to require a password
(open the page once with ?token=...; the browser then remembers it).
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import io
import os
import re
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
VENDOR = ROOT / "vendor" / "negpy"
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from fastapi import FastAPI, HTTPException, Request, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from simpleneg import engine  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
WORK = Path(os.environ.get("DUMBCONVERT_DATA", Path.home() / ".dumbconvert-web"))
TOKEN = os.environ.get("DUMBCONVERT_TOKEN", "")

# Fields the page may set. Everything else in Settings is decided by the engine.
EDITABLE = {"contrast", "density", "saturation", "cyan", "magenta", "yellow", "grayscale", "rotation",
            "fine_rotation", "mirror", "highlight_tone", "shadow_tone", "shadow_warmth", "shadow_tint",
            "highlight_warmth", "highlight_tint", "glow", "sharpen", "color_noise", "auto_crop"}
SETTINGS_FIELDS = {f.name: f for f in fields(engine.Settings)}

# One render thread: the engine keeps the decoded scan per thread, so this makes slider drags fast.
RENDER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="render")
EXPORT = ThreadPoolExecutor(max_workers=1, thread_name_prefix="export")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.loop = asyncio.get_running_loop()
    WORK.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="DumbConvert", docs_url=None, redoc_url=None, lifespan=lifespan)
photos: dict[str, dict] = {}     # id -> {"path": Path, "name": str, "outlier": bool}
roll: dict = {}                  # floors / ceils / axis shared by the frames of the session


@app.middleware("http")
async def password(request: Request, call_next):
    if not TOKEN:
        return await call_next(request)
    supplied = request.query_params.get("token") or request.cookies.get("dc_token") or ""
    if not hmac.compare_digest(supplied, TOKEN):
        return JSONResponse({"error": "password needed: open the page with ?token=..."}, status_code=401)
    response = await call_next(request)
    if request.query_params.get("token"):
        response.set_cookie("dc_token", TOKEN, httponly=True, samesite="strict", max_age=60 * 60 * 24 * 365)
    return response


def settings_from(data: dict, photo: dict) -> engine.Settings:
    st = engine.Settings()
    for key, value in (data or {}).items():
        if key not in EDITABLE:
            continue
        default = getattr(st, key)
        try:
            setattr(st, key, type(default)(value))
        except (TypeError, ValueError):
            raise HTTPException(400, f"bad value for {key}") from None
    if roll and not photo.get("outlier"):
        st.roll_floors, st.roll_ceils, st.roll_axis = roll["floors"], roll["ceils"], roll["axis"]
    stock = engine.stock_by_id(photo.get("film", "")) if photo.get("film") else None
    if stock is not None:
        engine.settings_for_stock(st, stock)
        st.grayscale = st.grayscale or bool(data.get("grayscale"))
    return st


def photo_or_404(photo_id: str) -> dict:
    photo = photos.get(photo_id)
    if photo is None:
        raise HTTPException(404, "unknown photo")
    return photo


def encode(arr) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "JPEG", quality=88)
    return buf.getvalue()


def analyze() -> None:
    """Measure the whole session as one roll, so frames share the same colour."""
    global roll
    frames = [(p["path"], engine.Settings()) for p in photos.values()]
    if len(frames) < 2:
        roll = {}
        for p in photos.values():
            p["outlier"] = False
        return
    floors, ceils, outliers, axis = engine.analyze_roll(frames)
    roll = {"floors": floors, "ceils": ceils, "axis": axis}
    for p, out in zip(photos.values(), outliers):
        p["outlier"] = out


@app.get("/api/info")
def info():
    return {
        "defaults": {k: getattr(engine.Settings(), k) for k in sorted(EDITABLE)},
        "formats": {k: v[0] for k, v in engine.EXPORT_FORMATS.items()},
        "color_spaces": engine.COLOR_SPACES,
        "films": [{"id": s["id"], "name": s["displayName"]} for s in engine.film_stocks()],
        "extensions": sorted(engine.IMAGE_EXTENSIONS),
    }


@app.get("/api/photos")
def list_photos():
    return [{"id": i, "name": p["name"], "film": p.get("film", "")} for i, p in photos.items()]


@app.post("/api/photos")
async def upload(files: list[UploadFile]):
    added = []
    for f in files:
        name = Path(f.filename or "scan").name
        if Path(name).suffix.lower() not in engine.IMAGE_EXTENSIONS:
            raise HTTPException(400, f"{name}: not a supported file type")
        photo_id = uuid.uuid4().hex[:12]
        folder = WORK / "uploads" / photo_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        with path.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        photos[photo_id] = {"path": path, "name": name, "outlier": False}
        added.append({"id": photo_id, "name": name})
    try:
        await app.state.loop.run_in_executor(RENDER, analyze)
    except Exception as exc:   # one odd file must not lose the upload: frames then use their own measurement
        print("roll analysis failed:", exc, file=sys.stderr)
    return added


@app.delete("/api/photos/{photo_id}")
async def remove(photo_id: str):
    photo = photo_or_404(photo_id)
    del photos[photo_id]
    shutil.rmtree(photo["path"].parent, ignore_errors=True)
    await app.state.loop.run_in_executor(RENDER, analyze)
    return {"ok": True}


@app.post("/api/photos/{photo_id}/film")
async def set_film(photo_id: str, body: dict):
    photo = photo_or_404(photo_id)
    photo["film"] = str(body.get("film", ""))
    return {"ok": True}


@app.post("/api/photos/{photo_id}/preview")
async def preview(photo_id: str, body: dict, long_edge: int = 1400):
    photo = photo_or_404(photo_id)
    st = settings_from(body, photo)
    long_edge = max(200, min(long_edge, 4000))

    def work():
        return encode(engine.preview(photo["path"], st, long_edge, keep_source=True))

    try:
        data = await app.state.loop.run_in_executor(RENDER, work)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/photos/{photo_id}/export")
async def export(photo_id: str, body: dict):
    photo = photo_or_404(photo_id)
    st = settings_from(body.get("settings", {}), photo)
    fmt = body.get("format", "jpg")
    if fmt not in engine.EXPORT_FORMATS:
        raise HTTPException(400, "unknown format")
    space = body.get("color_space", "sRGB")
    if space not in engine.COLOR_SPACES:
        raise HTTPException(400, "unknown colour space")
    opts = engine.ExportOptions(fmt=fmt, color_space=space, overwrite=True)
    size = int(body.get("long_edge") or 0)
    if size:
        opts.size, opts.long_edge = "long_edge", max(256, min(size, 20000))
    out_dir = WORK / "exports" / photo_id

    def work():
        return engine.export(photo["path"], out_dir, st, opts)

    try:
        out = await app.state.loop.run_in_executor(EXPORT, work)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    safe = re.sub(r"[^\w. -]", "_", out.name)
    return FileResponse(out, filename=safe, headers={"Cache-Control": "no-store"})


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


def main():
    import uvicorn
    ap = argparse.ArgumentParser(description="DumbConvert in the browser (for iPad and other tablets)")
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to reach it from other devices")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    if args.host not in ("127.0.0.1", "localhost") and not TOKEN:
        print("Warning: reachable from the network without a password. Set DUMBCONVERT_TOKEN.", file=sys.stderr)
    uvicorn.run(app, host=args.host, port=args.port)
