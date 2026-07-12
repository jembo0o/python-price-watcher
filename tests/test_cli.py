import unittest
from dataclasses import dataclass
from unittest.mock import patch

from price_watcher.cli import resolve_watchlist_game


@dataclass(frozen=True)
class FakeGamePrice:
    app_id: int
    name: str | None
    price_cents: int
    currency: str | None
    formatted: str
    is_free: bool


@dataclass(frozen=True)
class FakeGameSearchResult:
    app_id: int
    name: str
    price: str | None


class CliTests(unittest.TestCase):
    def test_resolve_watchlist_game_rejects_missing_identifier(self) -> None:
        with self.assertRaises(ValueError):
            resolve_watchlist_game(None, None, "us")

    def test_resolve_watchlist_game_rejects_app_id_and_query_together(self) -> None:
        with self.assertRaises(ValueError):
            resolve_watchlist_game(1245620, "elden ring", "us")

    def test_resolve_watchlist_game_by_app_id_uses_game_name_when_available(self) -> None:
        fake_price = FakeGamePrice(
            app_id=1245620,
            name="ELDEN RING",
            price_cents=5999,
            currency="USD",
            formatted="$59.99",
            is_free=False,
        )

        with patch(
            "price_watcher.steam_client.fetch_game_price",
            return_value=fake_price,
        ):
            self.assertEqual(
                resolve_watchlist_game(1245620, None, "us"),
                (1245620, "ELDEN RING"),
            )

    def test_resolve_watchlist_game_by_query_uses_first_match(self) -> None:
        fake_result = FakeGameSearchResult(
            app_id=1245620,
            name="ELDEN RING",
            price="$59.99",
        )

        with (
            patch(
                "price_watcher.steam_client.search_games",
                return_value=[fake_result],
            ),
            patch("builtins.print"),
        ):
            self.assertEqual(
                resolve_watchlist_game(None, "elden ring", "us"),
                (1245620, "ELDEN RING"),
            )


if __name__ == "__main__":
    unittest.main()
