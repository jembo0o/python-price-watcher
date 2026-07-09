from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any

from price_watcher.regions import get_steam_country_code


STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_STORE_SEARCH_URL = "https://store.steampowered.com/api/storesearch"


@dataclass(frozen=True)
class GamePrice:
    app_id: int
    name: str | None
    price_cents: int
    currency: str | None
    formatted: str
    is_free: bool


@dataclass(frozen=True)
class GameSearchResult:
    app_id: int
    name: str
    price: str | None


def fetch_game_price(app_id: int, region: str = "us") -> GamePrice | None:
    steam_country_code = get_steam_country_code(region)
    params = {
        "appids": app_id,
        "cc": steam_country_code,
        "filters": "basic,price_overview",
    }

    payload = _get_json(STEAM_APPDETAILS_URL, params)
    if payload is None:
        return None

    app_data = payload.get(str(app_id))
    if not isinstance(app_data, dict) or not app_data.get("success"):
        return None

    game_data = app_data.get("data")
    if not isinstance(game_data, dict):
        return None

    name = _get_optional_string(game_data.get("name"))
    is_free = game_data.get("is_free")
    if is_free is True:
        return GamePrice(
            app_id=app_id,
            name=name,
            price_cents=0,
            currency=None,
            formatted="free",
            is_free=True,
        )

    price_overview = game_data.get("price_overview")
    if not isinstance(price_overview, dict):
        return None

    final_price = price_overview.get("final")
    currency = price_overview.get("currency")
    final_formatted = price_overview.get("final_formatted")

    if (
        not isinstance(final_price, int)
        or not isinstance(currency, str)
        or not isinstance(final_formatted, str)
        or not final_formatted
    ):
        return None

    return GamePrice(
        app_id=app_id,
        name=name,
        price_cents=final_price,
        currency=currency,
        formatted=final_formatted,
        is_free=False,
    )


def search_games(
    query: str,
    region: str = "us",
    limit: int = 10,
) -> list[GameSearchResult]:
    normalized_query = query.strip()
    if not normalized_query or limit <= 0:
        return []

    steam_country_code = get_steam_country_code(region)
    results = _search_games_once(normalized_query, steam_country_code, limit)
    if results:
        return results

    return _search_games_by_tokens(normalized_query, steam_country_code, limit)


def _search_games_once(
    query: str,
    region: str,
    limit: int,
) -> list[GameSearchResult]:
    params = {
        "term": query,
        "cc": region,
        "l": "en",
    }
    payload = _get_json(STEAM_STORE_SEARCH_URL, params)
    if payload is None:
        return []

    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return []

    results: list[GameSearchResult] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue

        app_id = _get_app_id(raw_item.get("id"))
        name = raw_item.get("name")
        if app_id is None or not isinstance(name, str) or not name:
            continue

        results.append(
            GameSearchResult(
                app_id=app_id,
                name=name,
                price=_format_search_price(raw_item.get("price")),
            )
        )

        if len(results) >= limit:
            break

    return results


def _search_games_by_tokens(
    query: str,
    region: str,
    limit: int,
) -> list[GameSearchResult]:
    tokens = _get_search_tokens(query)
    if not tokens:
        return []

    candidates: dict[int, GameSearchResult] = {}
    for token in tokens:
        for result in _search_games_once(token, region, limit * 3):
            candidates.setdefault(result.app_id, result)

    ranked_results = sorted(
        candidates.values(),
        key=lambda result: _get_search_score(query, result.name),
        reverse=True,
    )
    return ranked_results[:limit]


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload: Any = response.json()
    except (requests.RequestException, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def _get_optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _get_search_tokens(query: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9]+", query.lower())
        if len(token) >= 3
    ][:3]


def _get_search_score(query: str, name: str) -> float:
    normalized_query = _normalize_search_text(query)
    normalized_name = _normalize_search_text(name)
    sequence_score = SequenceMatcher(None, normalized_query, normalized_name).ratio()

    query_tokens = _get_search_tokens(query)
    name_tokens = _get_search_tokens(name)
    if not query_tokens or not name_tokens:
        return sequence_score

    token_scores = [
        max(
            SequenceMatcher(None, query_token, name_token).ratio()
            for name_token in name_tokens
        )
        for query_token in query_tokens
    ]
    token_score = sum(token_scores) / len(token_scores)

    return (token_score * 0.7) + (sequence_score * 0.3)


def _normalize_search_text(value: str) -> str:
    return " ".join(_get_search_tokens(value))


def _get_app_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.isdigit():
        return int(value)

    return None


def _format_search_price(raw_price: Any) -> str | None:
    if not isinstance(raw_price, dict):
        return None

    final_formatted = raw_price.get("final_formatted")
    if isinstance(final_formatted, str) and final_formatted:
        return final_formatted

    final_price = raw_price.get("final")
    currency = raw_price.get("currency")
    if isinstance(final_price, int) and isinstance(currency, str):
        return f"{final_price / 100:.2f} {currency}"

    return None
