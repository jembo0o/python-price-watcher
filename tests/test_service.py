import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from price_watcher.service import PriceWatcherService
from price_watcher.steam_client import GamePrice, GameSearchResult
from price_watcher.watchlist import WatchItem, load_watchlist


class PriceWatcherServiceTests(unittest.TestCase):
    def test_get_price_normalizes_region(self) -> None:
        with patch(
            "price_watcher.steam_client.fetch_game_price",
            return_value=None,
        ) as fetch_game_price:
            PriceWatcherService().get_price(1245620, "Europe")

        fetch_game_price.assert_called_once_with(1245620, "eu")

    def test_add_watch_item_by_title_uses_best_search_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            watchlist_path = Path(temp_dir) / "watchlist.json"
            service = PriceWatcherService(watchlist_path=watchlist_path)
            search_result = GameSearchResult(
                app_id=1245620,
                name="ELDEN RING",
                price="$59.99",
            )

            with patch(
                "price_watcher.steam_client.search_games",
                return_value=[search_result],
            ):
                item = service.add_watch_item("Elden Ring", 2999, "eu")

            self.assertEqual(
                item,
                WatchItem(
                    app_id=1245620,
                    target_price_cents=2999,
                    region="eu",
                    name="ELDEN RING",
                ),
            )
            self.assertEqual(load_watchlist(watchlist_path), [item])

    def test_add_watch_item_by_id_uses_fetched_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            watchlist_path = Path(temp_dir) / "watchlist.json"
            service = PriceWatcherService(watchlist_path=watchlist_path)
            game_price = GamePrice(
                app_id=1245620,
                name="ELDEN RING",
                price_cents=5999,
                currency="USD",
                formatted="$59.99",
                is_free=False,
            )

            with patch(
                "price_watcher.steam_client.fetch_game_price",
                return_value=game_price,
            ):
                item = service.add_watch_item(1245620, 2999, "us")

            self.assertEqual(item.name, "ELDEN RING")
            self.assertEqual(load_watchlist(watchlist_path), [item])


if __name__ == "__main__":
    unittest.main()
