from __future__ import annotations

from typing import Any, Dict, List

import requests

from config import get_optional_serper_api_key


def _normalise_results(payload: Dict[str, Any], max_results: int) -> List[Dict[str, str]]:
    organic_results = payload.get("organic", [])
    formatted: List[Dict[str, str]] = []

    for item in organic_results[:max_results]:
        formatted.append(
            {
                "title": str(item.get("title", "Untitled")),
                "link": str(item.get("link", "")),
                "snippet": str(item.get("snippet", "")),
            }
        )

    return formatted


def format_search_results(results: List[Dict[str, str]]) -> str:
    if not results:
        return "No recent external results were found."

    lines: List[str] = []
    for index, item in enumerate(results, start=1):
        lines.append(
            f"{index}. {item['title']}\nSource: {item['link']}\nSummary: {item['snippet']}"
        )
    return "\n\n".join(lines)


def run_search_agent(query: str, max_results: int = 5) -> Dict[str, Any]:
    api_key = get_optional_serper_api_key()
    if not api_key:
        return {
            "status": "skipped",
            "results": [],
            "formatted_context": "SERPER_API_KEY is not configured, so external search was skipped.",
        }

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": query},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ConnectionError(f"Serper search failed: {exc}") from exc

    payload = response.json()
    results = _normalise_results(payload, max_results=max_results)
    return {
        "status": "success",
        "results": results,
        "formatted_context": format_search_results(results),
    }