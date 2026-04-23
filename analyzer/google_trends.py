from pytrends.request import TrendReq
from datetime import datetime


def analyze(keyword: str, timeframe: str = "today 3-m", geo: str = "") -> dict:
    try:
        pt = TrendReq(hl="es-419", tz=360)
        pt.build_payload([keyword], timeframe=timeframe, geo=geo)

        interest_df = pt.interest_over_time()
        related_topics = pt.related_topics()
        related_queries = pt.related_queries()

        peak_value = 0
        peak_date = None
        avg_interest = 0
        trend_direction = "estable"

        if not interest_df.empty and keyword in interest_df.columns:
            series = interest_df[keyword]
            peak_value = int(series.max())
            peak_date = series.idxmax().strftime("%Y-%m-%d") if peak_value > 0 else None
            avg_interest = round(float(series.mean()), 1)

            if len(series) >= 4:
                recent = series.iloc[-4:].mean()
                older = series.iloc[:4].mean()
                if recent > older * 1.15:
                    trend_direction = "subiendo"
                elif recent < older * 0.85:
                    trend_direction = "bajando"

        top_related = []
        if keyword in related_topics and related_topics[keyword].get("top") is not None:
            df = related_topics[keyword]["top"]
            top_related = df["topic_title"].head(5).tolist()

        rising_related = []
        if keyword in related_topics and related_topics[keyword].get("rising") is not None:
            df = related_topics[keyword]["rising"]
            rising_related = df["topic_title"].head(5).tolist()

        top_queries = []
        rising_queries = []
        if keyword in related_queries:
            if related_queries[keyword].get("top") is not None:
                top_queries = related_queries[keyword]["top"]["query"].head(10).tolist()
            if related_queries[keyword].get("rising") is not None:
                rising_queries = related_queries[keyword]["rising"]["query"].head(10).tolist()

        return {
            "source": "Google Trends",
            "keyword": keyword,
            "peak_interest": peak_value,
            "peak_date": peak_date,
            "avg_interest": avg_interest,
            "trend_direction": trend_direction,
            "related_topics": top_related,
            "rising_topics": rising_related,
            "top_searches": top_queries,
            "rising_searches": rising_queries,
            "error": None,
        }

    except Exception as e:
        return {"source": "Google Trends", "keyword": keyword, "error": str(e)}
