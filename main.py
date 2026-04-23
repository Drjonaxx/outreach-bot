#!/usr/bin/env python3
"""
Audience Analyzer - Analiza tendencias y preferencias de audiencia en multiples plataformas.

Uso:
    python main.py "moda sustentable"
    python main.py "recetas veganas" --geo MX
    python main.py "gaming" --timeframe "today 12-m"
"""

import argparse
import sys
from analyzer.aggregator import run_all
from report.generator import print_report
from rich.console import Console

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Analiza que le gusta a la gente sobre cualquier tema en Google, Reddit, HackerNews, YouTube y noticias.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("keyword", help='Tema a analizar (ej: "moda", "fitness", "tecnologia")')
    parser.add_argument(
        "--geo",
        default="",
        help="Codigo de pais para Google Trends (ej: MX, US, AR). Vacio = mundial.",
    )
    parser.add_argument(
        "--timeframe",
        default="today 3-m",
        help='Periodo para Google Trends (ej: "today 3-m", "today 12-m", "today 5-y").',
    )
    args = parser.parse_args()

    keyword = args.keyword.strip()
    if not keyword:
        console.print("[red]Error: debes ingresar un keyword.[/red]")
        sys.exit(1)

    console.print(f"\n[bold cyan]Analizando '[white]{keyword}[/white]' en todas las plataformas...[/bold cyan]")
    console.print("[dim]Esto puede tomar 10-30 segundos dependiendo de las APIs disponibles.[/dim]\n")

    results = run_all(keyword)
    print_report(keyword, results)


if __name__ == "__main__":
    main()
