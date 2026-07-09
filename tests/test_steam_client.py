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

    def test_fetch_game_price_maps_eu_region_to_steam_country_code(self) -> None:
        with patch("price_watcher.steam_client._get_json", return_value=None) as get_json:
            fetch_game_price(1245620, region="eu")

        self.assertEqual(get_json.call_args.args[1]["cc"], "de")

    def test_search_games_maps_ukraine_alias_to_steam_country_code(self) -> None:
        with patch("price_watcher.steam_client._get_json", return_value=None) as get_json:
            search_games("counter strike", region="ukraine")

        self.assertEqual(get_json.call_args.args[1]["cc"], "ua")

    def test_search_games_falls_back_to_token_search_for_typos(self) -> None:
        empty_payload = {"items": []}
        counter_payload = {
            "items": [
                {
                    "id": 730,
                    "name": "Counter-Strike 2",
                    "price": None,
                },
                {
                    "id": 10,
                    "name": "Counter-Strike",
                    "price": {
                        "final": 999,
                        "currency": "USD",
                        "final_formatted": "$9.99",
                    },
                },
            ]
        }

        with patch(
            "price_watcher.steam_client._get_json",
            side_effect=[empty_payload, counter_payload, empty_payload],
        ):
            self.assertEqual(
                search_games("counter stike", limit=3),
                [
                    GameSearchResult(
                        app_id=730,
                        name="Counter-Strike 2",
                        price=None,
                    ),
                    GameSearchResult(
                        app_id=10,
                        name="Counter-Strike",
                        price="$9.99",
                    ),
                ],
            )


if __name__ == "__main__":
    unittest.main()
