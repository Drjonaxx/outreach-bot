def calculate(results: dict) -> dict:
    score = 0.0

    gt = results.get("google_trends", {})
    if not gt.get("error"):
        avg = gt.get("avg_interest", 0)
        direction = gt.get("trend_direction", "estable")
        gt_score = min(avg * 0.3, 30)
        if direction == "subiendo":
            gt_score = min(gt_score * 1.2, 30)
        elif direction == "bajando":
            gt_score *= 0.8
        score += gt_score

    yt = results.get("youtube", {})
    if not yt.get("error"):
        avg_views = yt.get("avg_views", 0)
        n_channels = len(yt.get("top_channels", []))
        views_score = min(avg_views / 500_000 * 10, 25)
        diversity_score = min(n_channels * 3, 15)
        score += views_score + diversity_score

    nw = results.get("news", {})
    if not nw.get("error"):
        articles = min(nw.get("total_results", 0), 10)
        score += articles * 1.5

    hn = results.get("hackernews", {})
    if not hn.get("error"):
        posts = hn.get("posts_analyzed", 0)
        avg_pts = hn.get("avg_points", 0)
        score += min((posts + avg_pts) * 0.5, 15)

    score = round(min(score, 100))

    if score >= 70:
        verdict = "Oportunidad alta"
        color = "green"
    elif score >= 45:
        verdict = "Oportunidad moderada"
        color = "yellow"
    elif score >= 20:
        verdict = "Oportunidad baja"
        color = "orange"
    else:
        verdict = "Nicho muy pequeño"
        color = "red"

    return {"score": score, "verdict": verdict, "color": color}
