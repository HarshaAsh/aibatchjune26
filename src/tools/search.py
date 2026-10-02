"""Serper web-search integration for agent nodes."""

from typing import Any

import requests

from src.config import load_config


SERPER_SEARCH_URL = "https://google.serper.dev/search"


def serper_search(query: str) -> dict[str, Any]:
    """Search the web with Serper and return its JSON response.

    Returns an empty dictionary if configuration, the request, or response
    parsing fails. Error details are printed without exposing credentials.
    """
    try:
        api_key = load_config().serper_api_key
        response = requests.post(
            SERPER_SEARCH_URL,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": query},
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Serper returned a non-object JSON response.")
        return result
    except (requests.RequestException, ValueError) as exc:
        print(f"Serper search error: {exc}")
        return {}
