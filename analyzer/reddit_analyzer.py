from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET


def analyze(keyword: str) -> dict:
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return {
            "source": "Reddit",
            "keyword": keyword,
            "error": "Credenciales de Reddit no configuradas (ver .env.example)",
        }
    return {
        "source": "Reddit",
        "keyword": keyword,
        "error": "Reddit API temporalmente no disponible",
    }
