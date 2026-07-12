import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from price_watcher.checker import (
    format_cents,
    format_game_label,
)
from price_watcher.money import parse_price_to_cents
from price_watcher.notifier import get_telegram_chats, send_telegram_message
from price_watcher.regions import normalize_region
from price_watcher.runner import run_watch_loop, run_watch_once
from price_watcher.service import PriceWatcherService
from price_watcher.state import DEFAULT_STATE_PATH
from price_watcher.watchlist import DEFAULT_WATCHLIST_PATH

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
    watchlist_add_parser.add_argument("--app-id", type=int)
    watchlist_add_parser.add_argument(
        "--query",
        help="Find a Steam game by title and add the best match.",
    )
    watchlist_add_parser.add_argument(
        "--region",
        default="us",
        help="Steam region/country code, for example us, ua, eu.",
    )
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

    telegram_bot_parser = telegram_subparsers.add_parser(
        "bot",
        help="Run the interactive Telegram bot and price checks.",
    )
    telegram_bot_parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="Path to watchlist JSON file.",
    )
    telegram_bot_parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to notification state JSON file.",
    )
    telegram_bot_parser.add_argument(
        "--interval",
        type=int,
        help="Seconds between automatic price checks.",
    )
    telegram_bot_parser.add_argument(
        "--poll-timeout",
        type=int,
        default=25,
        help="Seconds for each Telegram long-poll request.",
    )
    telegram_bot_parser.add_argument(
        "--max-cycles",
        type=int,
        help="Stop after this many poll cycles. Useful for testing.",
    )
    return parser.parse_args()


def handle_price(app_id: int, region: str) -> int:
    price = PriceWatcherService().get_price(app_id, region)

    if price is None:
        print(f"{app_id}: price not found")
        return 1

    print(f"{format_game_label(price.app_id, price.name)}: {price.formatted}")
    return 0


def handle_search(query: str, region: str, limit: int) -> int:
    results = PriceWatcherService().search(query, region, limit)
    if not results:
        print("No games found.")
        return 1

    for result in results:
        price = result.price if result.price is not None else "no price"
        print(f"{format_game_label(result.app_id, result.name)}: {price}")

    return 0


def handle_watchlist_add(args: argparse.Namespace) -> int:
    target_price_cents = parse_price_to_cents(args.target_price)
    region = normalize_region(args.region)
    identifier = _get_watchlist_identifier(args.app_id, args.query)
    service = PriceWatcherService(watchlist_path=args.file)
    item = service.add_watch_item(
        identifier=identifier,
        target_price_cents=target_price_cents,
        region=region,
    )

    if args.query is not None:
        print(f"Matched {format_game_label(item.app_id, item.name)}")
    print(
        f"{format_game_label(item.app_id, item.name)} [{item.region}] saved "
        f"with target <= {format_cents(item.target_price_cents)}"
    )
    return 0


def resolve_watchlist_game(
    app_id: int | None,
    query: str | None,
    region: str,
) -> tuple[int, str | None]:
    if app_id is None and query is None:
        raise ValueError("Provide --app-id or --query")

    if app_id is not None and query is not None:
        raise ValueError("Use either --app-id or --query, not both")

    identifier = app_id if app_id is not None else query
    if identifier is None:
        raise ValueError("Provide --app-id or --query")

    return PriceWatcherService().resolve_game(identifier, region)


def handle_watchlist_list(path: Path) -> int:
    items = PriceWatcherService(watchlist_path=path).list_watch_items()

    if not items:
        print("Watchlist is empty.")
        return 0

    for item in items:
        target = format_cents(item.target_price_cents)
        print(
            f"{format_game_label(item.app_id, item.name)} "
            f"[{item.region}] target <= {target}"
        )

    return 0


def handle_watchlist_remove(args: argparse.Namespace) -> int:
    region = normalize_region(args.region) if args.region is not None else None
    result = PriceWatcherService(
        watchlist_path=args.file,
        state_path=args.state_file,
    ).remove_watch_item(
        app_id=args.app_id,
        region=region,
    )

    if result.removed_watch_items == 0:
        target = f"{args.app_id}"
        if region:
            target = f"{target} [{region}]"
        print(f"No watchlist item found for {target}.")
    else:
        print(f"Removed {result.removed_watch_items} watchlist item(s).")

    if result.removed_state_items:
        print(f"Removed {result.removed_state_items} notification state item(s).")

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


def handle_telegram_bot(args: argparse.Namespace) -> int:
    config = load_runtime_config()
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set"
        )

    interval_seconds = args.interval or config.check_interval_seconds

    try:
        from price_watcher.telegram_bot import TelegramPriceWatcherBot
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    bot = TelegramPriceWatcherBot(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        service=PriceWatcherService(
            watchlist_path=args.file,
            state_path=args.state_file,
        ),
        default_region=config.steam_region,
        check_interval_seconds=interval_seconds,
        poll_timeout_seconds=args.poll_timeout,
    )

    try:
        return bot.run(max_cycles=args.max_cycles)
    except KeyboardInterrupt:
        print("Telegram bot stopped.")
        return 130


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
        if args.telegram_command == "bot":
            return handle_telegram_bot(args)

        print("Choose a telegram command: chat-id, send-test, or bot.")
        return 2

    print(f"Unknown command: {args.command}")
    return 2


def _get_watchlist_identifier(
    app_id: int | None,
    query: str | None,
) -> int | str:
    if app_id is None and query is None:
        raise ValueError("Provide --app-id or --query")
    if app_id is not None and query is not None:
        raise ValueError("Use either --app-id or --query, not both")
    return app_id if app_id is not None else query or ""


if __name__ == "__main__":
    raise SystemExit(main())
