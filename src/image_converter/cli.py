from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from .converter import png_to_stl, png_to_svg, svg_to_stl

console = Console()


@click.group()
def main():
    """Converte imagens PNG em SVG e/ou STL."""


@main.command("to-svg")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.argument("output", type=click.Path(path_type=Path), required=False)
@click.option("--colormode", type=click.Choice(["binary", "color"]), default="binary", show_default=True, help="Modo de cor da vetorização.")
@click.option("--speckle", default=4, show_default=True, help="Remove ruídos menores que N pixels.")
@click.option("--corner", default=60, show_default=True, help="Limiar de detecção de cantos (0-180).")
def to_svg(input: Path, output: Path | None, colormode: str, speckle: int, corner: int):
    """Converte PNG em SVG.

    \b
    Exemplos:
      image-converter to-svg logo.png
      image-converter to-svg logo.png output/logo.svg --colormode color
    """
    output = output or input.with_suffix(".svg")

    with console.status(f"Vetorizando [bold]{input.name}[/bold]..."):
        try:
            result = png_to_svg(input, output, colormode=colormode, filter_speckle=speckle, corner_threshold=corner)
            console.print(Panel(f"[green]SVG salvo em:[/green] {result}", title="Concluído", border_style="green"))
        except Exception as e:
            console.print(Panel(f"[red]{e}[/red]", title="Erro", border_style="red"))
            raise SystemExit(1)


@main.command("to-stl")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.argument("output", type=click.Path(path_type=Path), required=False)
@click.option("--height", default=3.0, show_default=True, help="Altura de extrusão em mm.")
@click.option("--scale", default=1.0, show_default=True, help="Fator de escala.")
def to_stl(input: Path, output: Path | None, height: float, scale: float):
    """Converte SVG em STL.

    \b
    Exemplos:
      image-converter to-stl logo.svg
      image-converter to-stl logo.svg output/logo.stl --height 5 --scale 0.5
    """
    output = output or input.with_suffix(".stl")

    with console.status(f"Extrudando [bold]{input.name}[/bold]..."):
        try:
            result = svg_to_stl(input, output, height_mm=height, scale=scale)
            console.print(Panel(f"[green]STL salvo em:[/green] {result}", title="Concluído", border_style="green"))
        except Exception as e:
            console.print(Panel(f"[red]{e}[/red]", title="Erro", border_style="red"))
            raise SystemExit(1)


@main.command("convert")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.argument("output", type=click.Path(path_type=Path), required=False)
@click.option("--height", default=3.0, show_default=True, help="Altura de extrusão em mm.")
@click.option("--scale", default=1.0, show_default=True, help="Fator de escala.")
@click.option("--colormode", type=click.Choice(["binary", "color"]), default="binary", show_default=True, help="Modo de cor da vetorização.")
@click.option("--speckle", default=4, show_default=True, help="Remove ruídos menores que N pixels.")
@click.option("--keep-svg", is_flag=True, default=True, help="Mantém o SVG intermediário.")
def convert(input: Path, output: Path | None, height: float, scale: float, colormode: str, speckle: int, keep_svg: bool):
    """Pipeline completo: PNG → SVG → STL.

    \b
    Exemplos:
      image-converter convert logo.png
      image-converter convert logo.png output/logo.stl --height 5 --scale 0.5
    """
    output = output or input.with_suffix(".stl")

    console.print(f"\n[bold]Convertendo:[/bold] {input.name} → SVG → STL\n")

    with console.status("Passo 1/2 — Vetorizando PNG..."):
        try:
            svg_path, stl_path = png_to_stl(
                input, output,
                height_mm=height,
                scale=scale,
                colormode=colormode,
                filter_speckle=speckle,
            )
        except Exception as e:
            console.print(Panel(f"[red]{e}[/red]", title="Erro", border_style="red"))
            raise SystemExit(1)

    console.print(f"  [green]✓[/green] SVG: {svg_path}")
    console.print(f"  [green]✓[/green] STL: {stl_path}\n")
    console.print(Panel("[green]Conversão concluída com sucesso![/green]", border_style="green"))
