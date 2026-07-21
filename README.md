# image-converter

Converte imagens PNG em SVG e STL via interface web ou linha de comando.

## Docker (recomendado)

Não requer instalação local de dependências.

### Subir o servidor

```bash
docker compose up --build
```

Acesse a interface em **http://localhost:8000**.

### Parar o servidor

```bash
docker compose down
```

### Variáveis de ambiente opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `8000` | Porta exposta pelo container |

Para alterar a porta, edite o `docker-compose.yml`:

```yaml
ports:
  - "3000:8000"  # acessa em localhost:3000
```

---

## Instalação local

### Requisitos

- Python 3.10+
- OpenSCAD (para conversão STL)

```bash
# Ubuntu/Debian
sudo apt install openscad

# macOS
brew install openscad
```

### Instalação

```bash
# Apenas CLI
pip install -e .

# CLI + servidor web
pip install -e ".[web]"
```

### Servidor web local

```bash
uvicorn image_converter.web:app --reload
# Acesse http://localhost:8000
```

## Uso via CLI

### PNG → SVG → STL (pipeline completo)

```bash
image-converter convert logo.png
image-converter convert logo.png saida/logo.stl --height 5 --scale 0.5
```

### Apenas PNG → SVG

```bash
image-converter to-svg logo.png
image-converter to-svg logo.png saida/logo.svg --colormode color
```

### Apenas SVG → STL

```bash
image-converter to-stl logo.svg
image-converter to-stl logo.svg saida/logo.stl --height 5
```

### WEBP → PNG ou JPG

```bash
image-converter to-png logo.webp
image-converter to-jpg logo.webp saida/logo.jpg --quality 90
```

## Opções disponíveis

| Opção | Padrão | Descrição |
|---|---|---|
| `--height` | `3.0` | Altura de extrusão em mm |
| `--scale` | `1.0` | Fator de escala do modelo |
| `--colormode` | `binary` | `binary` (P&B) ou `color` |
| `--speckle` | `4` | Remove ruídos menores que N pixels |
| `--corner` | `60` | Sensibilidade de detecção de cantos |

## Como biblioteca Python

```python
from image_converter import png_to_svg, svg_to_stl, png_to_stl, convert_image
from pathlib import Path

# Pipeline completo
svg, stl = png_to_stl(Path("logo.png"), Path("logo.stl"), height_mm=5.0)

# Passo a passo
png_to_svg(Path("logo.png"), Path("logo.svg"))
svg_to_stl(Path("logo.svg"), Path("logo.stl"), height_mm=3.0)

# WEBP → PNG ou JPG
convert_image(Path("logo.webp"), Path("logo.png"))
convert_image(Path("logo.webp"), Path("logo.jpg"), quality=90)
```

## Testes

```bash
pip install pytest
pytest tests/
```
