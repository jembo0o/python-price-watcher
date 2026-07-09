from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from price_watcher.checker import (
    PriceCheckResult,
    PriceFetcher,
    build_price_drop_message,
    check_watchlist_items,
    format_check_result,
)
from price_watcher.notifier import send_telegram_message
from price_watcher.state import (
    DEFAULT_STATE_PATH,
    filter_notifiable_results,
    load_notification_state,
    mark_results_as_notified,
)
from price_watcher.watchlist import load_watchlist


OutputWriter = Callable[[str], None]
Sleeper = Callable[[int], None]


@dataclass(frozen=True)
class WatchRunResult:
    checked_count: int
    failed_count: int
    notification_sent: bool


def run_watch_once(
    watchlist_path: Path,
    notify: bool = False,
    telegram_bot_token: str | None = None,
    telegram_chat_id: str | None = None,
    state_path: Path = DEFAULT_STATE_PATH,
    output: OutputWriter = print,
    fetcher: PriceFetcher | None = None,
) -> WatchRunResult:
    items = load_watchlist(watchlist_path)
    if not items:
        output("Watchlist is empty.")
        return WatchRunResult(
            checked_count=0,
            failed_count=0,
            notification_sent=False,
        )

    results = check_watchlist_items(items, fetcher=fetcher)
    for result in results:
        output(format_check_result(result))

    notification_sent = False
    if notify:
        notification_sent = send_drop_notification(
            results=results,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            state_path=state_path,
            output=output,
        )

    failed_count = sum(1 for result in results if result.price is None)
    return WatchRunResult(
        checked_count=len(results),
        failed_count=failed_count,
        notification_sent=notification_sent,
    )


def run_watch_loop(
    watchlist_path: Path,
    interval_seconds: int,
    notify: bool = False,
    telegram_bot_token: str | None = None,
    telegram_chat_id: str | None = None,
    state_path: Path = DEFAULT_STATE_PATH,
    max_runs: int | None = None,
    output: OutputWriter = print,
    sleeper: Sleeper = time.sleep,
    fetcher: PriceFetcher | None = None,
) -> int:
    if interval_seconds <= 0:
        raise ValueError("Interval must be greater than 0")

    if max_runs is not None and max_runs <= 0:
        raise ValueError("Max runs must be greater than 0")

    run_number = 0
    last_exit_code = 0

    while max_runs is None or run_number < max_runs:
        run_number += 1
        output(f"Watch run #{run_number}")

        result = run_watch_once(
            watchlist_path=watchlist_path,
            notify=notify,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            state_path=state_path,
            output=output,
            fetcher=fetcher,
        )
        last_exit_code = 1 if result.failed_count else 0

        if max_runs is not None and run_number >= max_runs:
            break

        output(f"Sleeping for {interval_seconds} seconds...")
        sleeper(interval_seconds)

    return last_exit_code


def send_drop_notification(
    results: list[PriceCheckResult],
    telegram_bot_token: str | None,
    telegram_chat_id: str | None,
    state_path: Path = DEFAULT_STATE_PATH,
    output: OutputWriter = print,
) -> bool:
    state = load_notification_state(state_path)
    notifiable_results = filter_notifiable_results(results, state)
    message = build_price_drop_message(notifiable_results)
    if message is None:
        output("No new price drops to notify.")
        return False

    if not telegram_bot_token or not telegram_chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set to use --notify"
        )

    send_telegram_message(
        bot_token=telegram_bot_token,
        chat_id=telegram_chat_id,
        text=message,
    )
    mark_results_as_notified(state, notifiable_results, state_path)
    output("Telegram notification sent.")
    return True
