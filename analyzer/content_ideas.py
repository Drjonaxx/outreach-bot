from datetime import datetime


def generate(keyword: str, results: dict) -> list:
    yt = results.get("youtube", {})
    gt = results.get("google_trends", {})

    tags = yt.get("top_tags", []) if not yt.get("error") else []
    top_videos = yt.get("top_videos", []) if not yt.get("error") else []
    rising = gt.get("rising_searches", []) if not gt.get("error") else []

    year = datetime.now().year
    ideas = []

    t1 = f" ({tags[0]})" if tags else ""
    ideas.append(f"Cómo empezar con {keyword} desde cero{t1} — guía completa {year}")

    if rising:
        ideas.append(f"¿Qué es {rising[0]}? Todo lo que necesitas saber")
    elif len(tags) > 1:
        ideas.append(f"La verdad sobre {keyword} y {tags[1]} que nadie te dice")
    else:
        ideas.append(f"Lo que nadie te dice sobre {keyword}")

    n = len(top_videos) if top_videos else 5
    ideas.append(f"Los {n} errores más comunes en {keyword} (y cómo evitarlos)")

    if len(rising) > 1:
        ideas.append(f"{rising[0]} vs {rising[1]}: ¿cuál es mejor para ti?")
    elif len(tags) > 2:
        ideas.append(f"{tags[1]} vs {tags[2]}: la comparativa que nadie hizo")
    else:
        ideas.append(f"Hice esto con {keyword} por 30 días — estos son los resultados")

    if tags:
        ideas.append(f"Mis herramientas favoritas de {keyword} en {year} ({', '.join(tags[:3])})")
    else:
        ideas.append(f"Todo lo que aprendí sobre {keyword} en un año")

    return ideas[:5]
