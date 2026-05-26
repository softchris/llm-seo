"""Orchestrates all checks and computes the overall score."""

from __future__ import annotations

from .checks import (
    CheckResult,
    check_canonical_lang,
    check_content_clarity,
    check_headings,
    check_llms_txt,
    check_meta_description,
    check_open_graph,
    check_robots,
    check_semantic_html,
    check_sitemap,
    check_structured_data,
)
from .fetcher import fetch_page

ALL_CHECKS = [
    check_robots,
    check_llms_txt,
    check_sitemap,
    check_structured_data,
    check_semantic_html,
    check_meta_description,
    check_open_graph,
    check_content_clarity,
    check_headings,
    check_canonical_lang,
]


def _grade(score: int) -> dict:
    if score >= 90:
        return {"letter": "A", "label": "Excellent", "color": "#22c55e"}
    if score >= 75:
        return {"letter": "B", "label": "Good", "color": "#84cc16"}
    if score >= 60:
        return {"letter": "C", "label": "Fair", "color": "#eab308"}
    if score >= 40:
        return {"letter": "D", "label": "Poor", "color": "#f97316"}
    return {"letter": "F", "label": "Not Ready", "color": "#ef4444"}


async def analyze(url: str) -> dict:
    """Run all checks against a URL and return the full report."""
    data = await fetch_page(url)

    results: list[dict] = []
    total_score = 0

    for check_fn in ALL_CHECKS:
        result: CheckResult = check_fn(data)
        results.append(result.to_dict())
        total_score += result.score

    grade = _grade(total_score)

    return {
        "url": url,
        "resolved_url": data.get("page", {}).get("url", url),
        "score": total_score,
        "max_score": 100,
        "grade": grade,
        "checks": results,
    }
