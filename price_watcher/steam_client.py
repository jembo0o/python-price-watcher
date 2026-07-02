from dataclasses import dataclass
from typing import Any

import requests


STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


@dataclass(frozen=True)
class GamePrice:
    app_id: int
    price_cents: int
    currency: str | None
    formatted: str
    is_free: bool


def fetch_game_price(app_id: int, region: str = "us") -> GamePrice | None:
    params = {
        "appids": app_id,
        "cc": region,
        "filters": "basic,price_overview",
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

    is_free = game_data.get("is_free")
    if is_free is True:
        return GamePrice(
            app_id=app_id,
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
        price_cents=final_price,
        currency=currency,
        formatted=final_formatted,
        is_free=False,
    )
