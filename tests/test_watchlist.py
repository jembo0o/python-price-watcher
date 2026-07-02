import tempfile
import unittest
from pathlib import Path

from price_watcher.watchlist import WatchItem, load_watchlist, upsert_watch_item


class WatchlistTests(unittest.TestCase):
    def test_load_missing_watchlist_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"

            self.assertEqual(load_watchlist(path), [])

    def test_upsert_adds_new_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")

            upsert_watch_item(item, path)

            self.assertEqual(load_watchlist(path), [item])

    def test_upsert_updates_existing_item_for_same_app_and_region(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            first_item = WatchItem(app_id=1245620, target_price_cents=5999, region="us")
            updated_item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")

            upsert_watch_item(first_item, path)
            upsert_watch_item(updated_item, path)

            self.assertEqual(load_watchlist(path), [updated_item])


if __name__ == "__main__":
    unittest.main()
