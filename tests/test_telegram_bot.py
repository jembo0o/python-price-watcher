import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from price_watcher.notifier import TelegramUpdate
from price_watcher.service import PriceWatcherService, RemoveResult
from price_watcher.steam_client import GamePrice, GameSearchResult
from price_watcher.telegram_bot import (
    TelegramPriceWatcherBot,
    split_telegram_message,
)
from price_watcher.watchlist import WatchItem


class TelegramPriceWatcherBotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = Mock(spec=PriceWatcherService)
        self.service.watchlist_path = Path("watchlist.json")
        self.service.state_path = Path("state.json")
        self.bot = TelegramPriceWatcherBot(
            bot_token="token",
            chat_id="123",
            service=self.service,
            default_region="us",
            output=Mock(),
        )

    def test_search_command_uses_region_and_sends_results(self) -> None:
        self.service.search.return_value = [
            GameSearchResult(
                app_id=1245620,
                name="ELDEN RING",
                price="59,99EUR",
            )
        ]

        with patch("price_watcher.telegram_bot.send_telegram_message") as send:
            self.bot.handle_update(
                TelegramUpdate(
                    update_id=1,
                    chat_id=123,
                    text="/search region=eu Elden Ring",
                )
            )

        self.service.search.assert_called_once_with("Elden Ring", region="eu", limit=5)
        self.assertIn("ELDEN RING (1245620)", send.call_args.args[2])

    def test_add_command_accepts_title(self) -> None:
        self.service.add_watch_item.return_value = WatchItem(
            app_id=1245620,
            target_price_cents=2999,
            region="ua",
            name="ELDEN RING",
        )

        with patch("price_watcher.telegram_bot.send_telegram_message") as send:
            self.bot.handle_update(
                TelegramUpdate(
                    update_id=2,
                    chat_id=123,
                    text="/add 29.99 region=ua Elden Ring",
                )
            )

        self.service.add_watch_item.assert_called_once_with(
            identifier="Elden Ring",
            target_price_cents=2999,
            region="ua",
        )
        self.assertIn("Saved ELDEN RING", send.call_args.args[2])

    def test_price_command_accepts_app_id(self) -> None:
        self.service.get_price.return_value = GamePrice(
            app_id=1245620,
            name="ELDEN RING",
            price_cents=5999,
            currency="USD",
            formatted="$59.99",
            is_free=False,
        )

        with patch("price_watcher.telegram_bot.send_telegram_message") as send:
            self.bot.handle_update(
                TelegramUpdate(3, 123, "/price 1245620")
            )

        self.service.get_price.assert_called_once_with(1245620, "us")
        self.assertIn("$59.99", send.call_args.args[2])

    def test_remove_command_removes_all_regions_by_default(self) -> None:
        self.service.remove_watch_item.return_value = RemoveResult(2, 1)

        with patch("price_watcher.telegram_bot.send_telegram_message"):
            self.bot.handle_update(TelegramUpdate(4, 123, "/remove 1245620"))

        self.service.remove_watch_item.assert_called_once_with(1245620, None)

    def test_message_from_other_chat_is_denied(self) -> None:
        with patch("price_watcher.telegram_bot.send_telegram_message") as send:
            self.bot.handle_update(TelegramUpdate(5, 999, "/list"))

        self.service.list_watch_items.assert_not_called()
        self.assertEqual(send.call_args.args[2], "Access denied.")

    def test_run_can_stop_after_one_poll_cycle(self) -> None:
        with (
            patch.object(self.bot, "_register_commands") as register,
            patch.object(self.bot, "_run_scheduled_check") as scheduled_check,
            patch("price_watcher.telegram_bot.get_telegram_updates", return_value=[]),
        ):
            exit_code = self.bot.run(max_cycles=1)

        self.assertEqual(exit_code, 0)
        register.assert_called_once_with()
        scheduled_check.assert_called_once_with()


class TelegramMessageSplitTests(unittest.TestCase):
    def test_long_message_is_split_within_limit(self) -> None:
        chunks = split_telegram_message("first\nsecond\nthird", limit=12)

        self.assertEqual(chunks, ["first\nsecond", "third"])
        self.assertTrue(all(len(chunk) <= 12 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
