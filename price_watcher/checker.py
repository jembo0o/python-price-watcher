from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from price_watcher.watchlist import WatchItem

if TYPE_CHECKING:
    from price_watcher.steam_client import GamePrice


PriceFetcher = Callable[[int, str], "GamePrice | None"]


@dataclass(frozen=True)
class PriceCheckResult:
    item: WatchItem
    price: GamePrice | None
    is_target_met: bool


def check_watchlist_items(
    items: list[WatchItem],
    fetcher: PriceFetcher | None = None,
) -> list[PriceCheckResult]:
    if fetcher is None:
        try:
            from price_watcher.steam_client import fetch_game_price
        except ImportError as exc:
            raise RuntimeError(
                "Install dependencies with: pip install -r requirements.txt"
            ) from exc

        fetcher = fetch_game_price

    results: list[PriceCheckResult] = []

    for item in items:
        price = fetcher(item.app_id, item.region)
        results.append(
            PriceCheckResult(
                item=item,
                price=price,
                is_target_met=price is not None
                and price.price_cents <= item.target_price_cents,
            )
        )

    return results


def format_check_result(result: PriceCheckResult) -> str:
    item = result.item

    if result.price is None:
        game_label = format_game_label(item.app_id, item.name)
        return f"{game_label} [{item.region}]: price not found"

    game_label = format_game_label(item.app_id, result.price.name or item.name)
    target = format_cents(item.target_price_cents, result.price.currency)
    if result.is_target_met:
        return (
            f"DROP: {game_label} [{item.region}] "
            f"{result.price.formatted} <= {target}"
        )

    return (
        f"WAIT: {game_label} [{item.region}] "
        f"{result.price.formatted} > {target}"
    )


def build_price_drop_message(results: list[PriceCheckResult]) -> str | None:
    drop_lines = [
        format_check_result(result)
        for result in results
        if result.is_target_met and result.price is not None
    ]

    if not drop_lines:
        return None

    return "Steam price drop found:\n" + "\n".join(drop_lines)


def format_cents(price_cents: int, currency: str | None = None) -> str:
    formatted = f"{price_cents / 100:.2f}"
    if currency is None:
        return formatted
    return f"{formatted} {currency}"


def format_game_label(app_id: int, name: str | None = None) -> str:
    if name:
        return f"{name} ({app_id})"

    return str(app_id)
