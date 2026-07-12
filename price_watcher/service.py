from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from price_watcher import steam_client
from price_watcher.checker import PriceCheckResult, check_watchlist_items
from price_watcher.regions import normalize_region
from price_watcher.state import DEFAULT_STATE_PATH, remove_notification_state
from price_watcher.watchlist import (
    DEFAULT_WATCHLIST_PATH,
    WatchItem,
    load_watchlist,
    remove_watch_item,
    upsert_watch_item,
)


@dataclass(frozen=True)
class RemoveResult:
    removed_watch_items: int
    removed_state_items: int


class PriceWatcherService:
    """Application API shared by CLI, Telegram, and future interfaces."""

    def __init__(
        self,
        watchlist_path: Path = DEFAULT_WATCHLIST_PATH,
        state_path: Path = DEFAULT_STATE_PATH,
    ) -> None:
        self.watchlist_path = watchlist_path
        self.state_path = state_path

    def get_price(
        self,
        app_id: int,
        region: str = "us",
    ) -> steam_client.GamePrice | None:
        return steam_client.fetch_game_price(app_id, normalize_region(region))

    def search(
        self,
        query: str,
        region: str = "us",
        limit: int = 10,
    ) -> list[steam_client.GameSearchResult]:
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        return steam_client.search_games(
            query=query,
            region=normalize_region(region),
            limit=limit,
        )

    def add_watch_item(
        self,
        identifier: int | str,
        target_price_cents: int,
        region: str = "us",
    ) -> WatchItem:
        if target_price_cents < 0:
            raise ValueError("Target price must be greater than or equal to 0")

        normalized_region = normalize_region(region)
        app_id, name = self.resolve_game(identifier, normalized_region)
        item = WatchItem(
            app_id=app_id,
            target_price_cents=target_price_cents,
            region=normalized_region,
            name=name,
        )
        upsert_watch_item(item, self.watchlist_path)
        return item

    def list_watch_items(self) -> list[WatchItem]:
        return load_watchlist(self.watchlist_path)

    def remove_watch_item(
        self,
        app_id: int,
        region: str | None = None,
    ) -> RemoveResult:
        normalized_region = normalize_region(region) if region is not None else None
        _, removed_watch_items = remove_watch_item(
            app_id=app_id,
            region=normalized_region,
            path=self.watchlist_path,
        )
        _, removed_state_items = remove_notification_state(
            app_id=app_id,
            region=normalized_region,
            path=self.state_path,
        )
        return RemoveResult(
            removed_watch_items=removed_watch_items,
            removed_state_items=removed_state_items,
        )

    def check_watchlist(self) -> list[PriceCheckResult]:
        return check_watchlist_items(self.list_watch_items())

    def resolve_game(
        self,
        identifier: int | str,
        region: str,
    ) -> tuple[int, str | None]:
        if isinstance(identifier, int):
            price = self.get_price(identifier, region)
            return identifier, price.name if price is not None else None

        query = identifier.strip()
        if not query:
            raise ValueError("Game title must not be empty")

        if query.isdigit():
            return self.resolve_game(int(query), region)

        results = self.search(query=query, region=region, limit=1)
        if not results:
            raise ValueError(f"No Steam game found for query: {query}")

        best_match = results[0]
        return best_match.app_id, best_match.name
