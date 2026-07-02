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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    price = fetch_game_price(args.app_id)

    if price is None:
        print("Price not found. The game may be free, unavailable, or hidden by Steam.")
        return 1

    print(price)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
