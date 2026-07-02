from typing import Any

import requests


STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


def fetch_game_price(app_id: int, region: str = "us") -> str | None:
    params = {
        "appids": app_id,
        "cc": region,
        "filters": "price_overview",
    }

    try:
        response = requests.get(STEAM_APPDETAILS_URL, params=params, timeout=10)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError):
        return None

    app_data = payload.get(str(app_id))
    if not isinstance(app_data, dict) or not app_data.get("success"):
        return None

    game_data = app_data.get("data")
    if not isinstance(game_data, dict):
        return None

    price_overview = game_data.get("price_overview")
    if not isinstance(price_overview, dict):
        return None

    final_formatted = price_overview.get("final_formatted")
    if isinstance(final_formatted, str) and final_formatted:
        return final_formatted

    final_price = price_overview.get("final")
    currency = price_overview.get("currency")
    if isinstance(final_price, int) and isinstance(currency, str):
        return f"{final_price / 100:.2f} {currency}"

    return None
