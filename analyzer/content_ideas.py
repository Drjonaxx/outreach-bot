from datetime import datetime


def generate(keyword: str, results: dict) -> list:
    yt = results.get("youtube", {})
    gt = results.get("google_trends", {})

    top_videos = yt.get("top_videos", []) if not yt.get("error") else []
    rising = gt.get("rising_searches", []) if not gt.get("error") else []
    rising = [r for r in rising if len(r.split()) >= 2][:3]

    year = datetime.now().year
    ideas = []

    ideas.append(f"Cómo empezar con {keyword} desde cero — guía completa {year}")

    if rising:
        ideas.append(f"¿Por qué '{rising[0]}' está arrasando? Todo lo que necesitas saber")
    else:
        ideas.append(f"Lo que nadie te dice sobre {keyword} (y que cambia todo)")

    ideas.append(f"Probé {keyword} por 30 días — esto fue lo que pasó")

    if len(rising) > 1:
        ideas.append(f"'{rising[1]}': guía honesta para principiantes")
    else:
        ideas.append(f"Los errores más comunes en {keyword} que todos cometen")

    n = len(top_videos) if top_videos else 5
    ideas.append(f"Los {n} mejores {keyword} de {year}: cuál vale la pena")

    return ideas[:5]
