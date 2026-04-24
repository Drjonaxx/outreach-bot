import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from pytrends.request import TrendReq

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def google_trends(topic):
    print("\n📈 Google Trends...")
    try:
        pt = TrendReq(hl="es-419", tz=360)
        pt.build_payload([topic], timeframe="today 3-m")
        interest = pt.interest_over_time()
        related = pt.related_queries()

        if interest.empty:
            return {"error": "Sin datos de tendencias"}

        avg = int(interest[topic].mean())
        last = int(interest[topic].iloc[-1])
        trend = "subiendo" if last > avg else "bajando"

        top_queries = []
        if topic in related and related[topic]["top"] is not None:
            top_queries = related[topic]["top"]["query"].head(5).tolist()

        return {
            "promedio_interes": avg,
            "interes_actual": last,
            "tendencia": trend,
            "busquedas_relacionadas": top_queries,
        }
    except Exception as e:
        return {"error": str(e)}


def hackernews(topic):
    print("💻 HackerNews...")
    try:
        url = "https://hn.algolia.com/api/v1/search"
        params = {"query": topic, "tags": "story", "hitsPerPage": 5}
        res = requests.get(url, params=params, timeout=10)
        hits = res.json().get("hits", [])

        stories = []
        for h in hits:
            stories.append({
                "titulo": h.get("title"),
                "puntos": h.get("points", 0),
                "comentarios": h.get("num_comments", 0),
                "url": h.get("url", ""),
            })
        return {"historias": stories}
    except Exception as e:
        return {"error": str(e)}


def youtube(topic):
    print("▶️  YouTube...")
    if not YOUTUBE_API_KEY:
        return {"error": "Falta YOUTUBE_API_KEY en .env"}
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": topic,
            "type": "video",
            "order": "viewCount",
            "maxResults": 5,
            "key": YOUTUBE_API_KEY,
        }
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("items", [])

        videos = []
        for item in items:
            snippet = item.get("snippet", {})
            videos.append({
                "titulo": snippet.get("title"),
                "canal": snippet.get("channelTitle"),
                "fecha": snippet.get("publishedAt", "")[:10],
                "descripcion": snippet.get("description", "")[:120],
            })
        return {"videos": videos}
    except Exception as e:
        return {"error": str(e)}


def newsapi(topic):
    print("📰 NewsAPI...")
    if not NEWS_API_KEY:
        return {"error": "Falta NEWS_API_KEY en .env"}
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": topic,
            "sortBy": "popularity",
            "pageSize": 5,
            "language": "es",
            "apiKey": NEWS_API_KEY,
        }
        res = requests.get(url, params=params, timeout=10)
        articles = res.json().get("articles", [])

        noticias = []
        for a in articles:
            noticias.append({
                "titulo": a.get("title"),
                "fuente": a.get("source", {}).get("name"),
                "fecha": (a.get("publishedAt") or "")[:10],
                "url": a.get("url"),
            })
        return {"noticias": noticias}
    except Exception as e:
        return {"error": str(e)}


def reporte(topic):
    print(f"\n🔍 Analizando: '{topic}'")
    print("=" * 50)

    datos = {
        "tema": topic,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "google_trends": google_trends(topic),
        "hackernews": hackernews(topic),
        "youtube": youtube(topic),
        "newsapi": newsapi(topic),
    }

    print("\n" + "=" * 50)
    print(f"REPORTE: {topic.upper()}")
    print("=" * 50)

    # Google Trends
    gt = datos["google_trends"]
    if "error" not in gt:
        print(f"\n📈 TENDENCIA EN GOOGLE")
        print(f"  Interés actual: {gt['interes_actual']}/100")
        print(f"  Promedio últimos 3 meses: {gt['promedio_interes']}/100")
        print(f"  Está: {gt['tendencia'].upper()}")
        if gt["busquedas_relacionadas"]:
            print(f"  Búsquedas relacionadas: {', '.join(gt['busquedas_relacionadas'])}")

    # HackerNews
    hn = datos["hackernews"]
    if "error" not in hn and hn["historias"]:
        print(f"\n💻 TOP EN HACKERNEWS")
        for s in hn["historias"]:
            print(f"  • {s['titulo']} ({s['puntos']} pts, {s['comentarios']} comentarios)")

    # YouTube
    yt = datos["youtube"]
    if "error" not in yt and yt["videos"]:
        print(f"\n▶️  TOP VIDEOS EN YOUTUBE")
        for v in yt["videos"]:
            print(f"  • {v['titulo']}")
            print(f"    Canal: {v['canal']} | Fecha: {v['fecha']}")

    # NewsAPI
    na = datos["newsapi"]
    if "error" not in na and na["noticias"]:
        print(f"\n📰 NOTICIAS RECIENTES")
        for n in na["noticias"]:
            print(f"  • {n['titulo']}")
            print(f"    Fuente: {n['fuente']} | Fecha: {n['fecha']}")

    print("\n" + "=" * 50)
    return datos


if __name__ == "__main__":
    tema = input("¿Qué tema quieres analizar? → ").strip()
    if tema:
        reporte(tema)
    else:
        print("Por favor ingresa un tema.")
