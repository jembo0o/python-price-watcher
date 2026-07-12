import tempfile
import unittest
from pathlib import Path

from price_watcher.watchlist import (
    WatchItem,
    load_watchlist,
    remove_watch_item,
    upsert_watch_item,
)


class WatchlistTests(unittest.TestCase):
    def test_load_missing_watchlist_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"

            self.assertEqual(load_watchlist(path), [])

    def test_upsert_adds_new_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            item = WatchItem(
                app_id=1245620,
                target_price_cents=2999,
                region="us",
                name="ELDEN RING",
            )

            upsert_watch_item(item, path)

            self.assertEqual(load_watchlist(path), [item])

    def test_load_watchlist_supports_items_without_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            path.write_text(
                '[{"app_id": 1245620, "target_price_cents": 2999, "region": "us"}]',
                encoding="utf-8",
            )

            self.assertEqual(
                load_watchlist(path),
                [WatchItem(app_id=1245620, target_price_cents=2999, region="us")],
            )

    def test_upsert_updates_existing_item_for_same_app_and_region(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            first_item = WatchItem(app_id=1245620, target_price_cents=5999, region="us")
            updated_item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")

            upsert_watch_item(first_item, path)
            upsert_watch_item(updated_item, path)

            self.assertEqual(load_watchlist(path), [updated_item])

    def test_remove_watch_item_removes_all_regions_when_region_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            first_item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
            second_item = WatchItem(app_id=1245620, target_price_cents=2999, region="de")
            other_item = WatchItem(app_id=1086940, target_price_cents=4999, region="us")

            upsert_watch_item(first_item, path)
            upsert_watch_item(second_item, path)
            upsert_watch_item(other_item, path)

            remaining_items, removed_count = remove_watch_item(1245620, path=path)

            self.assertEqual(removed_count, 2)
            self.assertEqual(remaining_items, [other_item])
            self.assertEqual(load_watchlist(path), [other_item])

    def test_remove_watch_item_can_remove_one_region(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            first_item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
            second_item = WatchItem(app_id=1245620, target_price_cents=2999, region="de")

            upsert_watch_item(first_item, path)
            upsert_watch_item(second_item, path)

            remaining_items, removed_count = remove_watch_item(
                1245620,
                region="us",
                path=path,
            )

            self.assertEqual(removed_count, 1)
            self.assertEqual(remaining_items, [second_item])
            self.assertEqual(load_watchlist(path), [second_item])


if __name__ == "__main__":
    unittest.main()
