import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

from price_watcher.checker import (
    format_cents,
    format_game_label,
)
from price_watcher.notifier import get_telegram_chats, send_telegram_message
from price_watcher.regions import normalize_region
from price_watcher.runner import run_watch_loop, run_watch_once
from price_watcher.state import DEFAULT_STATE_PATH, remove_notification_state
from price_watcher.watchlist import (
    DEFAULT_WATCHLIST_PATH,
    WatchItem,
    load_watchlist,
    remove_watch_item,
    upsert_watch_item,
)

if TYPE_CHECKING:
    from price_watcher.config import Config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track Steam game prices.")
    parser.add_argument(
        "--app-id",
        type=int,
        help="Steam application ID, for example 730.",
    )
    parser.add_argument(
        "--region",
        default="us",
        help="Steam region/country code, for example us, ua, eu.",
    )

    subparsers = parser.add_subparsers(dest="command")

    price_parser = subparsers.add_parser("price", help="Fetch one Steam game price.")
    price_parser.add_argument(
        "--app-id",
        type=int,
        required=True,
        help="Steam application ID, for example 730.",
    )
    price_parser.add_argument(
        "--region",
        default="us",
        help="Steam region/country code, for example us, ua, eu.",
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search Steam games by title.",
    )
    search_parser.add_argument(
        "--query",
        required=True,
        help="Game title to search for, for example 'elden ring'.",
    )
    search_parser.add_argument(
        "--region",
        default="us",
        help="Steam region/country code, for example us, ua, eu.",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to show.",
    )

    watchlist_parser = subparsers.add_parser(
        "watchlist",
        help="Manage the local watchlist.",
    )
    watchlist_subparsers = watchlist_parser.add_subparsers(dest="watchlist_command")

    watchlist_add_parser = watchlist_subparsers.add_parser(
        "add",
        help="Add or update a game in the watchlist.",
    )
    watchlist_add_parser.add_argument("--app-id", type=int, required=True)
    watchlist_add_parser.add_argument("--region", default="us")
    watchlist_add_parser.add_argument(
        "--target-price",
        required=True,
        help="Target price as a decimal number, for example 29.99.",
    )
    watchlist_add_parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to watchlist JSON file.",
    )

    watchlist_remove_parser = watchlist_subparsers.add_parser(
        "remove",
        help="Remove a game from the watchlist.",
    )
    watchlist_remove_parser.add_argument("--app-id", type=int, required=True)
    watchlist_remove_parser.add_argument(
        "--region",
        help="Remove only this region. If omitted, all regions for app ID are removed.",
    )
    watchlist_remove_parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to watchlist JSON file.",
    )
    watchlist_remove_parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to notification state JSON file.",
    )

    watchlist_list_parser = watchlist_subparsers.add_parser(
        "list",
        help="Show saved watchlist items.",
    )
    watchlist_list_parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to watchlist JSON file.",
    )

    watchlist_check_parser = watchlist_subparsers.add_parser(
        "check",
        help="Fetch current prices for all watchlist items.",
    )
    watchlist_check_parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to watchlist JSON file.",
    )
    watchlist_check_parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to notification state JSON file.",
    )
    watchlist_check_parser.add_argument(
        "--notify",
        action="store_true",
        help="Send a Telegram message when a target price is reached.",
    )

    watch_parser = subparsers.add_parser(
        "watch",
        help="Continuously check the watchlist.",
    )
    watch_parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to watchlist JSON file.",
    )
    watch_parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to notification state JSON file.",
    )
    watch_parser.add_argument(
        "--interval",
        type=int,
        help="Seconds between checks. Defaults to CHECK_INTERVAL_SECONDS.",
    )
    watch_parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Telegram messages when target prices are reached.",
    )
    watch_parser.add_argument(
        "--max-runs",
        type=int,
        help="Stop after this many checks. Useful for testing.",
    )

    telegram_parser = subparsers.add_parser(
        "telegram",
        help="Set up and test Telegram notifications.",
    )
    telegram_subparsers = telegram_parser.add_subparsers(dest="telegram_command")

    telegram_subparsers.add_parser(
        "chat-id",
        help="Show chat IDs from recent messages sent to the bot.",
    )

    telegram_test_parser = telegram_subparsers.add_parser(
        "send-test",
        help="Send a test Telegram notification.",
    )
    telegram_test_parser.add_argument(
        "--message",
        default="Price watcher test notification.",
        help="Text to send to Telegram.",
    )
    return parser.parse_args()


def handle_price(app_id: int, region: str) -> int:
    try:
        from price_watcher.steam_client import fetch_game_price
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    price = fetch_game_price(app_id, normalize_region(region))

    if price is None:
        print(f"{app_id}: price not found")
        return 1

    print(f"{format_game_label(price.app_id, price.name)}: {price.formatted}")
    return 0


def handle_search(query: str, region: str, limit: int) -> int:
    try:
        from price_watcher.steam_client import search_games
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    if limit <= 0:
        raise ValueError("Limit must be greater than 0")

    results = search_games(query=query, region=normalize_region(region), limit=limit)
    if not results:
        print("No games found.")
        return 1

    for result in results:
        price = result.price if result.price is not None else "no price"
        print(f"{format_game_label(result.app_id, result.name)}: {price}")

    return 0


def handle_watchlist_add(args: argparse.Namespace) -> int:
    target_price_cents = _parse_price_to_cents(args.target_price)
    item = WatchItem(
        app_id=args.app_id,
        target_price_cents=target_price_cents,
        region=normalize_region(args.region),
    )

    upsert_watch_item(item, args.file)
    print(
        f"{item.app_id} [{item.region}] saved "
        f"with target <= {format_cents(item.target_price_cents)}"
    )
    return 0


def handle_watchlist_list(path: Path) -> int:
    items = load_watchlist(path)

    if not items:
        print("Watchlist is empty.")
        return 0

    for item in items:
        target = format_cents(item.target_price_cents)
        print(f"{item.app_id} [{item.region}] target <= {target}")

    return 0


def handle_watchlist_remove(args: argparse.Namespace) -> int:
    region = normalize_region(args.region) if args.region is not None else None
    _, removed_count = remove_watch_item(
        app_id=args.app_id,
        region=region,
        path=args.file,
    )
    _, removed_state_count = remove_notification_state(
        app_id=args.app_id,
        region=region,
        path=args.state_file,
    )

    if removed_count == 0:
        target = f"{args.app_id}"
        if region:
            target = f"{target} [{region}]"
        print(f"No watchlist item found for {target}.")
    else:
        print(f"Removed {removed_count} watchlist item(s).")

    if removed_state_count:
        print(f"Removed {removed_state_count} notification state item(s).")

    return 0


def handle_watchlist_check(
    path: Path,
    state_path: Path,
    notify: bool = False,
) -> int:
    telegram_bot_token, telegram_chat_id = get_notification_credentials(notify)
    result = run_watch_once(
        watchlist_path=path,
        notify=notify,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        state_path=state_path,
    )
    return 1 if result.failed_count else 0


def handle_watch(args: argparse.Namespace) -> int:
    config = load_runtime_config()
    interval_seconds = args.interval
    if interval_seconds is None:
        interval_seconds = config.check_interval_seconds

    telegram_bot_token = config.telegram_bot_token if args.notify else None
    telegram_chat_id = config.telegram_chat_id if args.notify else None

    print(
        f"Watching {args.file} every {interval_seconds} seconds. "
        "Press Ctrl+C to stop."
    )

    try:
        return run_watch_loop(
            watchlist_path=args.file,
            interval_seconds=interval_seconds,
            notify=args.notify,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            state_path=args.state_file,
            max_runs=args.max_runs,
        )
    except KeyboardInterrupt:
        print("Stopped.")
        return 130


def get_notification_credentials(notify: bool) -> tuple[str | None, str | None]:
    if not notify:
        return None, None

    config = load_runtime_config()
    return config.telegram_bot_token, config.telegram_chat_id


def handle_telegram_chat_id() -> int:
    config = load_runtime_config()
    if not config.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set")

    chats = get_telegram_chats(config.telegram_bot_token)
    if not chats:
        print("No chats found. Send any message to your bot, then run this again.")
        return 1

    for chat in chats:
        name = f" ({chat.name})" if chat.name else ""
        print(f"{chat.chat_id} [{chat.chat_type}]{name}")

    return 0


def handle_telegram_send_test(message: str) -> int:
    config = load_runtime_config()
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set"
        )

    send_telegram_message(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        text=message,
    )
    print("Telegram test message sent.")
    return 0


def load_runtime_config() -> "Config":
    try:
        from price_watcher.config import load_config
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    return load_config()


def main() -> int:
    args = parse_args()

    try:
        return dispatch(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1


def dispatch(args: argparse.Namespace) -> int:
    if args.command is None:
        if args.app_id is None:
            print(
                "Provide --app-id or use a command. "
                "Try: python -m price_watcher.cli price --app-id 730"
            )
            return 2
        return handle_price(args.app_id, args.region)

    if args.command == "price":
        return handle_price(args.app_id, args.region)

    if args.command == "search":
        return handle_search(args.query, args.region, args.limit)

    if args.command == "watchlist":
        if args.watchlist_command == "add":
            return handle_watchlist_add(args)
        if args.watchlist_command == "remove":
            return handle_watchlist_remove(args)
        if args.watchlist_command == "list":
            return handle_watchlist_list(args.file)
        if args.watchlist_command == "check":
            return handle_watchlist_check(args.file, args.state_file, args.notify)

        print("Choose a watchlist command: add, remove, list, or check.")
        return 2

    if args.command == "watch":
        return handle_watch(args)

    if args.command == "telegram":
        if args.telegram_command == "chat-id":
            return handle_telegram_chat_id()
        if args.telegram_command == "send-test":
            return handle_telegram_send_test(args.message)

        print("Choose a telegram command: chat-id or send-test.")
        return 2

    print(f"Unknown command: {args.command}")
    return 2


def _parse_price_to_cents(raw_price: str) -> int:
    try:
        value = Decimal(raw_price)
    except InvalidOperation as exc:
        raise ValueError("Target price must be a decimal number") from exc

    if value < 0:
        raise ValueError("Target price must be greater than or equal to 0")

    cents = value * Decimal("100")
    if cents != cents.to_integral_value():
        raise ValueError("Target price must have no more than two decimal places")

    return int(cents)


if __name__ == "__main__":
    raise SystemExit(main())
