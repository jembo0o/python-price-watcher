import unittest
from dataclasses import dataclass

from price_watcher.checker import (
    build_price_drop_message,
    check_watchlist_items,
    format_check_result,
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


class CheckerTests(unittest.TestCase):
    def test_check_marks_target_as_met(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")

        results = check_watchlist_items([item], fetcher=self._fake_fetcher(1999))

        self.assertTrue(results[0].is_target_met)

    def test_check_marks_target_as_not_met(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")

        results = check_watchlist_items([item], fetcher=self._fake_fetcher(5999))

        self.assertFalse(results[0].is_target_met)

    def test_check_handles_missing_price(self) -> None:
        item = WatchItem(app_id=1, target_price_cents=999, region="us")

        results = check_watchlist_items([item], fetcher=lambda app_id, region: None)

        self.assertIsNone(results[0].price)
        self.assertFalse(results[0].is_target_met)

    def test_format_drop_result(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
        result = check_watchlist_items([item], fetcher=self._fake_fetcher(1999))[0]

        self.assertEqual(
            format_check_result(result),
            "DROP: ELDEN RING (1245620) [us] $19.99 <= 29.99 USD",
        )

    def test_build_price_drop_message_returns_none_without_drops(self) -> None:
        item = WatchItem(app_id=1245620, target_price_cents=2999, region="us")
        results = check_watchlist_items([item], fetcher=self._fake_fetcher(5999))

        self.assertIsNone(build_price_drop_message(results))

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
