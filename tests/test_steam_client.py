import unittest
from unittest.mock import patch

from price_watcher.steam_client import (
    GamePrice,
    GameSearchResult,
    fetch_game_price,
    search_games,
)


class SteamClientTests(unittest.TestCase):
    def test_fetch_game_price_includes_game_name(self) -> None:
        payload = {
            "1245620": {
                "success": True,
                "data": {
                    "name": "ELDEN RING",
                    "is_free": False,
                    "price_overview": {
                        "final": 5999,
                        "currency": "USD",
                        "final_formatted": "$59.99",
                    },
                },
            }
        }

        with patch("price_watcher.steam_client._get_json", return_value=payload):
            self.assertEqual(
                fetch_game_price(1245620),
                GamePrice(
                    app_id=1245620,
                    name="ELDEN RING",
                    price_cents=5999,
                    currency="USD",
                    formatted="$59.99",
                    is_free=False,
                ),
            )

    def test_search_games_returns_search_results(self) -> None:
        payload = {
            "items": [
                {
                    "id": 1245620,
                    "name": "ELDEN RING",
                    "price": {
                        "final": 5999,
                        "currency": "USD",
                        "final_formatted": "$59.99",
                    },
                }
            ]
        }

        with patch("price_watcher.steam_client._get_json", return_value=payload):
            self.assertEqual(
                search_games("elden ring"),
                [
                    GameSearchResult(
                        app_id=1245620,
                        name="ELDEN RING",
                        price="$59.99",
                    )
                ],
            )

    def test_search_games_returns_empty_list_for_blank_query(self) -> None:
        self.assertEqual(search_games(""), [])


if __name__ == "__main__":
    unittest.main()
