import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

from price_watcher.checker import (
    PriceCheckResult,
    build_price_drop_message,
    check_watchlist_items,
    format_check_result,
    format_cents,
)
from price_watcher.notifier import send_telegram_message
from price_watcher.watchlist import (
    DEFAULT_WATCHLIST_PATH,
    WatchItem,
    load_watchlist,
    upsert_watch_item,
)


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
        help="Steam region/country code, for example us, de, ro.",
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
        help="Steam region/country code, for example us, de, ro.",
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
        "--notify",
        action="store_true",
        help="Send a Telegram message when a target price is reached.",
    )
    return parser.parse_args()


def handle_price(app_id: int, region: str) -> int:
    try:
        from price_watcher.steam_client import fetch_game_price
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    price = fetch_game_price(app_id, region)

    if price is None:
        print(f"{app_id}: price not found")
        return 1

    print(f"{price.app_id}: {price.formatted}")
    return 0


def handle_watchlist_add(args: argparse.Namespace) -> int:
    target_price_cents = _parse_price_to_cents(args.target_price)
    item = WatchItem(
        app_id=args.app_id,
        target_price_cents=target_price_cents,
        region=args.region,
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


def handle_watchlist_check(path: Path, notify: bool = False) -> int:
    items = load_watchlist(path)

    if not items:
        print("Watchlist is empty.")
        return 0

    results = check_watchlist_items(items)

    for result in results:
        print(format_check_result(result))

    if notify:
        send_drop_notification(results)

    failed_checks = sum(1 for result in results if result.price is None)
    return 1 if failed_checks else 0


def send_drop_notification(results: list[PriceCheckResult]) -> None:
    message = build_price_drop_message(results)
    if message is None:
        print("No price drops to notify.")
        return

    from price_watcher.config import load_config

    config = load_config()
    if not config.telegram_bot_token or not config.telegram_chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set to use --notify"
        )

    send_telegram_message(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
        text=message,
    )
    print("Telegram notification sent.")


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

    if args.command == "watchlist":
        if args.watchlist_command == "add":
            return handle_watchlist_add(args)
        if args.watchlist_command == "list":
            return handle_watchlist_list(args.file)
        if args.watchlist_command == "check":
            return handle_watchlist_check(args.file, args.notify)

        print("Choose a watchlist command: add, list, or check.")
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
