import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from price_watcher.runner import run_watch_loop, run_watch_once
from price_watcher.state import load_notification_state
from price_watcher.watchlist import WatchItem, save_watchlist


@dataclass(frozen=True)
class FakeGamePrice:
    app_id: int
    name: str
    price_cents: int
    currency: str
    formatted: str
    is_free: bool = False


class RunnerTests(unittest.TestCase):
    def test_run_watch_once_prints_check_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            save_watchlist(
                [WatchItem(app_id=1245620, target_price_cents=2999, region="us")],
                path,
            )
            output_lines: list[str] = []

            result = run_watch_once(
                watchlist_path=path,
                output=output_lines.append,
                fetcher=self._fake_fetcher(5999),
            )

            self.assertEqual(result.checked_count, 1)
            self.assertEqual(result.failed_count, 0)
            self.assertEqual(
                output_lines,
                ["WAIT: ELDEN RING (1245620) [us] $59.99 > 29.99 USD"],
            )

    def test_run_watch_loop_stops_after_max_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "watchlist.json"
            save_watchlist(
                [WatchItem(app_id=1245620, target_price_cents=2999, region="us")],
                path,
            )
            output_lines: list[str] = []
            sleep_calls: list[int] = []

            exit_code = run_watch_loop(
                watchlist_path=path,
                interval_seconds=5,
                max_runs=2,
                output=output_lines.append,
                sleeper=sleep_calls.append,
                fetcher=self._fake_fetcher(5999),
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(sleep_calls, [5])
            self.assertEqual(output_lines[0], "Watch run #1")
            self.assertIn("Sleeping for 5 seconds...", output_lines)
            self.assertIn("Watch run #2", output_lines)

    def test_run_watch_loop_rejects_invalid_interval(self) -> None:
        with self.assertRaises(ValueError):
            run_watch_loop(
                watchlist_path=Path("watchlist.json"),
                interval_seconds=0,
                max_runs=1,
            )

    def test_run_watch_once_notifies_first_drop_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            watchlist_path = Path(temp_dir) / "watchlist.json"
            state_path = Path(temp_dir) / "state.json"
            save_watchlist(
                [WatchItem(app_id=1245620, target_price_cents=2999, region="us")],
                watchlist_path,
            )
            output_lines: list[str] = []

            with patch("price_watcher.runner.send_telegram_message") as send_message:
                first_result = run_watch_once(
                    watchlist_path=watchlist_path,
                    notify=True,
                    telegram_bot_token="token",
                    telegram_chat_id="chat",
                    state_path=state_path,
                    output=output_lines.append,
                    fetcher=self._fake_fetcher(1999),
                )
                second_result = run_watch_once(
                    watchlist_path=watchlist_path,
                    notify=True,
                    telegram_bot_token="token",
                    telegram_chat_id="chat",
                    state_path=state_path,
                    output=output_lines.append,
                    fetcher=self._fake_fetcher(1999),
                )

            self.assertTrue(first_result.notification_sent)
            self.assertFalse(second_result.notification_sent)
            self.assertEqual(send_message.call_count, 1)
            self.assertIn("No new price drops to notify.", output_lines)
            self.assertEqual(
                load_notification_state(state_path)[
                    "1245620:us"
                ].last_notified_price_cents,
                1999,
            )

    def test_run_watch_once_notifies_again_when_price_drops_lower(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            watchlist_path = Path(temp_dir) / "watchlist.json"
            state_path = Path(temp_dir) / "state.json"
            output_lines: list[str] = []
            save_watchlist(
                [WatchItem(app_id=1245620, target_price_cents=2999, region="us")],
                watchlist_path,
            )

            with patch("price_watcher.runner.send_telegram_message") as send_message:
                first_result = run_watch_once(
                    watchlist_path=watchlist_path,
                    notify=True,
                    telegram_bot_token="token",
                    telegram_chat_id="chat",
                    state_path=state_path,
                    output=output_lines.append,
                    fetcher=self._fake_fetcher(1999),
                )
                second_result = run_watch_once(
                    watchlist_path=watchlist_path,
                    notify=True,
                    telegram_bot_token="token",
                    telegram_chat_id="chat",
                    state_path=state_path,
                    output=output_lines.append,
                    fetcher=self._fake_fetcher(999),
                )

            self.assertTrue(first_result.notification_sent)
            self.assertTrue(second_result.notification_sent)
            self.assertEqual(send_message.call_count, 2)
            self.assertEqual(
                load_notification_state(state_path)[
                    "1245620:us"
                ].last_notified_price_cents,
                999,
            )

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


if __name__ == "__main__":
    unittest.main()
