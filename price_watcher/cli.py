import argparse

from price_watcher.steam_client import fetch_game_price


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a Steam game price.")
    parser.add_argument(
        "--app-id",
        type=int,
        required=True,
        help="Steam application ID, for example 730.",
    )
    parser.add_argument(
        "--region",
        default="us",
        help="Steam region/country code, for example us, de, ro.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    price = fetch_game_price(args.app_id, args.region)

    if price is None:
        print(f"{args.app_id}: price not found")
        return 1

    print(f"{price.app_id}: {price.formatted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
