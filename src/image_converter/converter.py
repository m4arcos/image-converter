import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import vtracer
from PIL import Image, UnidentifiedImageError


def convert_image(
    input_path: Path,
    output_path: Path,
    quality: int = 95,
) -> Path:
    """Converte uma imagem raster (ex: WEBP) para PNG ou JPG usando Pillow.

    O formato de saída é definido pela extensão de output_path.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    target_format = output_path.suffix.lstrip(".").upper()
    if target_format == "JPG":
        target_format = "JPEG"
    if target_format not in ("PNG", "JPEG"):
        raise ValueError(f"Formato de saída não suportado: {output_path.suffix}")

    save_kwargs = {}
    try:
        with Image.open(input_path) as img:
            img.load()
            if target_format == "JPEG":
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                save_kwargs["quality"] = quality
            img.save(output_path, target_format, **save_kwargs)
    except UnidentifiedImageError as e:
        raise ValueError(f"Arquivo de imagem inválido ou corrompido: {input_path.name}") from e

    return output_path


def png_to_svg(
    input_path: Path,
    output_path: Path,
    colormode: str = "binary",
    filter_speckle: int = 4,
    corner_threshold: int = 60,
    length_threshold: float = 4.0,
    path_precision: int = 3,
) -> Path:
    """Converte PNG em SVG usando vtracer."""
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    normalized_path = _normalize_to_png(input_path)
    try:
        vtracer.convert_image_to_svg_py(
            str(normalized_path),
            str(output_path),
            colormode=colormode,
            filter_speckle=filter_speckle,
            color_precision=6,
            layer_difference=16,
            corner_threshold=corner_threshold,
            length_threshold=length_threshold,
            max_iterations=10,
            splice_threshold=45,
            path_precision=path_precision,
        )
    finally:
        normalized_path.unlink(missing_ok=True)

    return output_path


def svg_to_stl(
    input_path: Path,
    output_path: Path,
    height_mm: float = 3.0,
    scale: float = 1.0,
    size_mm: float | None = None,
) -> Path:
    """Converte SVG em STL usando OpenSCAD.

    Se size_mm for fornecido, calcula o scale automaticamente para que a maior
    dimensão do objeto (X ou Y) corresponda ao valor em milímetros.
    """
    _check_openscad()

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    if size_mm is not None:
        max_dim = _svg_max_dimension(input_path)
        if max_dim > 0:
            scale = size_mm / max_dim

    output_path.parent.mkdir(parents=True, exist_ok=True)

    scad_script = (
        f'scale([{scale}, {scale}, 1]) '
        f'linear_extrude(height={height_mm}) '
        f'import("{input_path.resolve()}");'
    )

    with tempfile.NamedTemporaryFile(suffix=".scad", mode="w", delete=False) as f:
        f.write(scad_script)
        scad_path = Path(f.name)

    try:
        cmd = _openscad_cmd(["-o", str(output_path), str(scad_path)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"OpenSCAD falhou:\n{result.stderr}")
    finally:
        scad_path.unlink(missing_ok=True)

    return output_path


def png_to_stl(
    input_path: Path,
    output_path: Path,
    height_mm: float = 3.0,
    scale: float = 1.0,
    size_mm: float | None = None,
    colormode: str = "binary",
    filter_speckle: int = 4,
) -> tuple[Path, Path]:
    """Pipeline completo: PNG → SVG → STL. Retorna (svg_path, stl_path)."""
    svg_path = output_path.with_suffix(".svg")

    png_to_svg(
        input_path,
        svg_path,
        colormode=colormode,
        filter_speckle=filter_speckle,
    )

    svg_to_stl(svg_path, output_path, height_mm=height_mm, scale=scale, size_mm=size_mm)

    return svg_path, output_path


def _normalize_to_png(input_path: Path) -> Path:
    """Reencoda a imagem de entrada como PNG usando Pillow.

    O decodificador de imagem do vtracer não suporta todas as variantes de WEBP
    (ex: com canal alpha ou modo lossless) e falha com um panic em Rust nesses
    casos, em vez de uma exceção Python normal. Reencodar sempre via Pillow
    evita esse problema para qualquer formato de entrada suportado por ele.
    """
    try:
        with Image.open(input_path) as img:
            img.load()
            has_alpha = "A" in img.mode or "transparency" in img.info
            target_mode = "RGBA" if has_alpha else "RGB"
            if img.mode != target_mode:
                img = img.convert(target_mode)

            fd, tmp_name = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            img.save(tmp_name, "PNG")
    except UnidentifiedImageError as e:
        raise ValueError(f"Arquivo de imagem inválido ou corrompido: {input_path.name}") from e

    return Path(tmp_name)


def _check_openscad() -> None:
    result = subprocess.run(["which", "openscad"], capture_output=True)
    if result.returncode != 0:
        raise EnvironmentError(
            "OpenSCAD não encontrado. Instale com:\n"
            "  Ubuntu/Debian: sudo apt install openscad\n"
            "  macOS:         brew install openscad"
        )


def _svg_max_dimension(svg_path: Path) -> float:
    """Retorna a maior dimensão (largura ou altura) do SVG em unidades do usuário."""
    root = ET.parse(svg_path).getroot()
    tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
    if tag != 'svg':
        return 0.0

    viewbox = root.get('viewBox') or root.get('viewbox')
    if viewbox:
        parts = re.split(r'[\s,]+', viewbox.strip())
        if len(parts) == 4:
            return max(float(parts[2]), float(parts[3]))

    def _strip_units(val: str) -> float:
        cleaned = re.sub(r'[^\d.]', '', val)
        return float(cleaned) if cleaned else 0.0

    w = _strip_units(root.get('width', '0'))
    h = _strip_units(root.get('height', '0'))
    return max(w, h)


def _openscad_cmd(args: list[str]) -> list[str]:
    """Prefixa com xvfb-run quando não há display disponível (ex: Docker)."""
    if not os.environ.get("DISPLAY"):
        return ["xvfb-run", "-a", "openscad"] + args
    return ["openscad"] + args
