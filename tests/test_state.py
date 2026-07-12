import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from price_watcher.checker import check_watchlist_items
from price_watcher.state import (
    NotificationState,
    filter_notifiable_results,
    load_notification_state,
    mark_results_as_notified,
    remove_notification_state,
)
from price_watcher.watchlist import WatchItem


@dataclass(frozen=True)
class FakeGamePrice:
    app_id: int
    name: str
    price_cents: int
    currency: str
    formatted: str
    is_free: bool = False


class StateTests(unittest.TestCase):
    def test_load_missing_state_returns_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"

            self.assertEqual(load_notification_state(path), {})

    def test_first_drop_is_notifiable(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
        result = check_watchlist_items([item], fetcher=self._fake_fetcher(1999))[0]

        self.assertEqual(filter_notifiable_results([result], {}), [result])

    def test_same_drop_price_is_not_notifiable_twice(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
        result = check_watchlist_items([item], fetcher=self._fake_fetcher(1999))[0]
        state = {
            "1245620:us": NotificationState(
                last_notified_price_cents=1999,
                target_price_cents=2999,
            )
        }

        self.assertEqual(filter_notifiable_results([result], state), [])

    def test_lower_drop_price_is_notifiable_again(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
        result = check_watchlist_items([item], fetcher=self._fake_fetcher(999))[0]
        state = {
            "1245620:us": NotificationState(
                last_notified_price_cents=1999,
                target_price_cents=2999,
            )
        }

        self.assertEqual(filter_notifiable_results([result], state), [result])

    def test_changed_target_is_notifiable_as_a_new_condition(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=3999, region="us")
        result = check_watchlist_items([item], fetcher=self._fake_fetcher(1999))[0]
        state = {
            "1245620:us": NotificationState(
                last_notified_price_cents=1999,
                target_price_cents=2999,
            )
        }

        self.assertEqual(filter_notifiable_results([result], state), [result])

    def test_mark_results_as_notified_writes_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
            result = check_watchlist_items([item], fetcher=self._fake_fetcher(1999))[0]

            mark_results_as_notified({}, [result], path)

            self.assertEqual(
                load_notification_state(path),
                {
                    "1245620:us": NotificationState(
                        last_notified_price_cents=1999,
                        target_price_cents=2999,
                    )
                },
            )

    def test_remove_notification_state_removes_all_regions_by_app_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            item_us = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
            item_de = WatchItem(app_id=1245620, target_price_cents=2999, region="de")
            result_us = check_watchlist_items(
                [item_us],
                fetcher=self._fake_fetcher(1999),
            )[0]
            result_de = check_watchlist_items(
                [item_de],
                fetcher=self._fake_fetcher(1999),
            )[0]
            mark_results_as_notified({}, [result_us, result_de], path)

            updated_state, removed_count = remove_notification_state(
                1245620,
                path=path,
            )

            self.assertEqual(removed_count, 2)
            self.assertEqual(updated_state, {})
            self.assertEqual(load_notification_state(path), {})

    def test_remove_notification_state_can_remove_one_region(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            item_us = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
            item_de = WatchItem(app_id=1245620, target_price_cents=2999, region="de")
            result_us = check_watchlist_items(
                [item_us],
                fetcher=self._fake_fetcher(1999),
            )[0]
            result_de = check_watchlist_items(
                [item_de],
                fetcher=self._fake_fetcher(1999),
            )[0]
            mark_results_as_notified({}, [result_us, result_de], path)

            updated_state, removed_count = remove_notification_state(
                1245620,
                region="us",
                path=path,
            )

            self.assertEqual(removed_count, 1)
            self.assertEqual(list(updated_state), ["1245620:de"])
            self.assertEqual(list(load_notification_state(path)), ["1245620:de"])

    @staticmethod
    def _fake_fetcher(price_cents: int):
        def fetcher(app_id: int, region: str) -> FakeGamePrice:
            return FakeGamePrice(
                app_id=app_id,
                name="ELDEN RING",
                price_cents=price_cents,
                currency="USD",
                formatted=f"${price_cents / 100:.2f}",
            )

        return fetcher
