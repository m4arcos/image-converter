import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .converter import convert_image, png_to_svg, svg_to_stl

UPLOAD_DIR = Path("/tmp/image-converter")
STATIC_DIR = Path(__file__).parent / "static"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
IMAGE_CONVERT_EXTENSIONS = {"png": ".png", "jpg": ".jpg"}

executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(title="Image Converter")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    mode: str = Form("both"),
    height: float = Form(3.0),
    size_mm: Optional[float] = Form(None),
    colormode: str = Form("binary"),
    speckle: int = Form(4),
):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        sent_ext = Path(file.filename).suffix or "(sem extensão)"
        raise HTTPException(
            400,
            f"Apenas arquivos PNG, JPG, JPEG ou WEBP são aceitos. Você enviou: {sent_ext}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Arquivo muito grande. Limite: 20 MB.")

    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir()

    stem = Path(file.filename).stem
    input_path = job_dir / file.filename
    input_path.write_bytes(content)

    files = []

    try:
        import asyncio

        loop = asyncio.get_event_loop()

        if mode in IMAGE_CONVERT_EXTENSIONS:
            ext = IMAGE_CONVERT_EXTENSIONS[mode]
            image_path = job_dir / f"{stem}{ext}"
            await loop.run_in_executor(
                executor,
                lambda: convert_image(input_path, image_path),
            )
            files.append({"type": mode, "name": image_path.name, "url": f"/files/{job_id}/{image_path.name}"})
        else:
            svg_path = job_dir / f"{stem}.svg"
            await loop.run_in_executor(
                executor,
                lambda: png_to_svg(
                    input_path,
                    svg_path,
                    colormode=colormode,
                    filter_speckle=speckle,
                ),
            )
            files.append({"type": "svg", "name": svg_path.name, "url": f"/files/{job_id}/{svg_path.name}"})

            if mode == "both":
                stl_path = job_dir / f"{stem}.stl"
                await loop.run_in_executor(
                    executor,
                    lambda: svg_to_stl(svg_path, stl_path, height_mm=height, size_mm=size_mm),
                )
                files.append({"type": "stl", "name": stl_path.name, "url": f"/files/{job_id}/{stl_path.name}"})

    except ValueError as e:
        raise HTTPException(400, str(e))
    except EnvironmentError as e:
        raise HTTPException(503, str(e))
    except HTTPException:
        raise
    except BaseException as e:
        # Captura também panics de código Rust (ex: pyo3_runtime.PanicException),
        # que herdam de BaseException e não seriam pegos por "except Exception".
        raise HTTPException(500, f"Falha na conversão: {e}")

    return {"job_id": job_id, "files": files}


@app.get("/files/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    safe_name = Path(filename).name
    file_path = UPLOAD_DIR / job_id / safe_name
    if not file_path.exists():
        raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(file_path, filename=safe_name)
