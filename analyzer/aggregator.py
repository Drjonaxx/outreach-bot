from concurrent.futures import ThreadPoolExecutor, as_completed
from analyzer import google_trends, reddit_analyzer, hackernews, youtube_analyzer, news_analyzer


def run_all(keyword: str) -> dict:
    tasks = {
        "google_trends": lambda: google_trends.analyze(keyword),
        "reddit": lambda: reddit_analyzer.analyze(keyword),
        "hackernews": lambda: hackernews.analyze(keyword),
        "youtube": lambda: youtube_analyzer.analyze(keyword),
        "news": lambda: news_analyzer.analyze(keyword),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"source": name, "keyword": keyword, "error": str(e)}

    return results
