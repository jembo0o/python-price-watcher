import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

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
    return parser.parse_args()


def handle_price(app_id: int, region: str) -> int:
    from price_watcher.steam_client import fetch_game_price

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
        f"with target <= {_format_cents(item.target_price_cents)}"
    )
    return 0


def handle_watchlist_list(path: Path) -> int:
    items = load_watchlist(path)

    if not items:
        print("Watchlist is empty.")
        return 0

    for item in items:
        target = _format_cents(item.target_price_cents)
        print(f"{item.app_id} [{item.region}] target <= {target}")

    return 0


def handle_watchlist_check(path: Path) -> int:
    from price_watcher.steam_client import fetch_game_price

    items = load_watchlist(path)

    if not items:
        print("Watchlist is empty.")
        return 0

    failed_checks = 0

    for item in items:
        price = fetch_game_price(item.app_id, item.region)
        if price is None:
            print(f"{item.app_id} [{item.region}]: price not found")
            failed_checks += 1
            continue

        target = _format_cents(item.target_price_cents, price.currency)
        if price.price_cents <= item.target_price_cents:
            print(f"DROP: {item.app_id} [{item.region}] {price.formatted} <= {target}")
        else:
            print(f"WAIT: {item.app_id} [{item.region}] {price.formatted} > {target}")

    return 1 if failed_checks else 0


def main() -> int:
    args = parse_args()

    try:
        return dispatch(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2


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
            return handle_watchlist_check(args.file)

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


def _format_cents(price_cents: int, currency: str | None = None) -> str:
    formatted = f"{price_cents / 100:.2f}"
    if currency is None:
        return formatted
    return f"{formatted} {currency}"


if __name__ == "__main__":
    raise SystemExit(main())
