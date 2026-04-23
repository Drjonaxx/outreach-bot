from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from datetime import datetime

console = Console()


def _section(title: str, color: str = "cyan") -> None:
    console.print(f"\n[bold {color}]{title}[/bold {color}]")


def _error_notice(source: str, error: str) -> None:
    console.print(f"  [dim yellow]⚠ {source}: {error}[/dim yellow]")


def print_report(keyword: str, results: dict) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    console.print(Panel(
        f"[bold white]Analisis de Audiencia[/bold white]\n"
        f"[dim]Keyword: [bold cyan]{keyword}[/bold cyan]  |  Generado: {now}[/dim]",
        box=box.DOUBLE_EDGE,
        style="blue",
    ))

    # ── Google Trends ──────────────────────────────────────────────
    _section("Google Trends", "green")
    gt = results.get("google_trends", {})
    if gt.get("error"):
        _error_notice("Google Trends", gt["error"])
    else:
        console.print(f"  Interes promedio : [bold]{gt.get('avg_interest', 'N/A')}[/bold] / 100")
        console.print(f"  Tendencia        : [bold]{gt.get('trend_direction', 'N/A')}[/bold]")
        console.print(f"  Pico de interes  : {gt.get('peak_interest', 'N/A')} el {gt.get('peak_date', 'N/A')}")
        if gt.get("top_searches"):
            console.print("  Busquedas top    : " + ", ".join(gt["top_searches"][:6]))
        if gt.get("rising_searches"):
            console.print("  Busquedas en alza: " + ", ".join(gt["rising_searches"][:6]))
        if gt.get("rising_topics"):
            console.print("  Temas en alza    : " + ", ".join(gt["rising_topics"][:5]))

    # ── Reddit ─────────────────────────────────────────────────────
    _section("Reddit", "orange3")
    rd = results.get("reddit", {})
    if rd.get("error"):
        _error_notice("Reddit", rd["error"])
    else:
        console.print(f"  Posts analizados : {rd.get('posts_analyzed', 0)}")
        console.print(f"  Upvotes promedio : {rd.get('avg_upvotes', 0)}")
        console.print(f"  Hora pico (UTC)  : {rd.get('peak_post_hour_utc', 'N/A')}:00 h")
        if rd.get("subreddits_found"):
            console.print("  Subreddits       : r/" + ", r/".join(rd["subreddits_found"][:5]))
        if rd.get("popular_flairs"):
            console.print("  Categorias pop.  : " + ", ".join(rd["popular_flairs"][:5]))
        if rd.get("top_posts"):
            table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
            table.add_column("Titulo", max_width=55)
            table.add_column("Upvotes", justify="right")
            table.add_column("Comentarios", justify="right")
            for p in rd["top_posts"][:3]:
                table.add_row(p["title"][:55], str(p["upvotes"]), str(p["comments"]))
            console.print(table)

    # ── HackerNews ────────────────────────────────────────────────
    _section("HackerNews", "bright_yellow")
    hn = results.get("hackernews", {})
    if hn.get("error"):
        _error_notice("HackerNews", hn["error"])
    else:
        console.print(f"  Posts analizados : {hn.get('posts_analyzed', 0)}")
        console.print(f"  Puntos promedio  : {hn.get('avg_points', 0)}")
        console.print(f"  Comentarios prom.: {hn.get('avg_comments', 0)}")
        if hn.get("top_domains"):
            console.print("  Fuentes top      : " + ", ".join(hn["top_domains"][:5]))
        if hn.get("top_posts"):
            for p in hn["top_posts"][:3]:
                console.print(f"  [{p['points']} pts] {p['title'][:60]}")

    # ── YouTube ───────────────────────────────────────────────────
    _section("YouTube", "red")
    yt = results.get("youtube", {})
    if yt.get("error"):
        _error_notice("YouTube", yt["error"])
    else:
        console.print(f"  Videos analizados: {yt.get('videos_analyzed', 0)}")
        console.print(f"  Vistas promedio  : {yt.get('avg_views', 0):,}")
        console.print(f"  Likes promedio   : {yt.get('avg_likes', 0):,}")
        if yt.get("top_channels"):
            console.print("  Canales top      : " + ", ".join(yt["top_channels"][:5]))
        if yt.get("top_tags"):
            console.print("  Tags populares   : " + ", ".join(yt["top_tags"][:8]))
        if yt.get("top_videos"):
            for v in yt["top_videos"][:3]:
                console.print(f"  [{v['views']:,} vistas] {v['title'][:55]}")

    # ── Noticias ──────────────────────────────────────────────────
    _section("Noticias (NewsAPI)", "magenta")
    nw = results.get("news", {})
    if nw.get("error"):
        _error_notice("NewsAPI", nw["error"])
    else:
        console.print(f"  Articulos totales: {nw.get('total_results', 0)}")
        console.print(f"  Dia mas activo   : {nw.get('busiest_news_day', 'N/A')}")
        if nw.get("top_sources"):
            console.print("  Medios top       : " + ", ".join(nw["top_sources"][:5]))
        if nw.get("top_articles"):
            for a in nw["top_articles"][:3]:
                console.print(f"  [{a['source']}] {a['title'][:60]}")

    # ── Resumen de contenido ──────────────────────────────────────
    _section("Recomendaciones de contenido", "bold white")
    _print_content_tips(keyword, results)

    console.print()


def _print_content_tips(keyword: str, results: dict) -> None:
    tips = []

    gt = results.get("google_trends", {})
    if not gt.get("error"):
        direction = gt.get("trend_direction", "")
        if direction == "subiendo":
            tips.append(f"El interes en '{keyword}' esta subiendo: es buen momento para publicar.")
        elif direction == "bajando":
            tips.append(f"El interes en '{keyword}' esta bajando: busca un angulo fresco o subtema.")
        if gt.get("rising_searches"):
            tips.append("Subtemas en alza para usar como contenido: " + ", ".join(gt["rising_searches"][:4]))

    rd = results.get("reddit", {})
    if not rd.get("error") and rd.get("peak_post_hour_utc") is not None:
        h = rd["peak_post_hour_utc"]
        tips.append(f"La audiencia es mas activa alrededor de las {h}:00 UTC. Publica cerca de ese horario.")

    yt = results.get("youtube", {})
    if not yt.get("error") and yt.get("top_tags"):
        tips.append("Tags de YouTube con mas engagement: " + ", ".join(yt["top_tags"][:6]))

    if not tips:
        tips.append("Configura las APIs (Reddit, YouTube, NewsAPI) para obtener recomendaciones personalizadas.")

    for i, tip in enumerate(tips, 1):
        console.print(f"  [bold]{i}.[/bold] {tip}")
