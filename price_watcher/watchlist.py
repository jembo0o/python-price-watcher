import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_WATCHLIST_PATH = Path("watchlist.json")


@dataclass(frozen=True)
class WatchItem:
    app_id: int
    target_price_cents: int
    region: str = "us"
    name: str | None = None


def load_watchlist(path: Path = DEFAULT_WATCHLIST_PATH) -> list[WatchItem]:
    if not path.exists():
        return []

    try:
        raw_items: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid watchlist JSON: {path}") from exc

    if not isinstance(raw_items, list):
        raise ValueError("Watchlist must contain a JSON array")

    return [_parse_watch_item(raw_item) for raw_item in raw_items]


def save_watchlist(
    items: list[WatchItem],
    path: Path = DEFAULT_WATCHLIST_PATH,
) -> None:
    path.write_text(
        json.dumps([asdict(item) for item in items], indent=2),
        encoding="utf-8",
    )


def upsert_watch_item(
    item: WatchItem,
    path: Path = DEFAULT_WATCHLIST_PATH,
) -> list[WatchItem]:
    items = load_watchlist(path)
    updated_items: list[WatchItem] = []
    item_was_updated = False

    for current_item in items:
        if current_item.app_id == item.app_id and current_item.region == item.region:
            updated_items.append(item)
            item_was_updated = True
        else:
            updated_items.append(current_item)

    if not item_was_updated:
        updated_items.append(item)

    save_watchlist(updated_items, path)
    return updated_items


def remove_watch_item(
    app_id: int,
    region: str | None = None,
    path: Path = DEFAULT_WATCHLIST_PATH,
) -> tuple[list[WatchItem], int]:
    items = load_watchlist(path)
    remaining_items: list[WatchItem] = []
    removed_count = 0

    for item in items:
        region_matches = region is None or item.region == region
        if item.app_id == app_id and region_matches:
            removed_count += 1
            continue

        remaining_items.append(item)

    if removed_count:
        save_watchlist(remaining_items, path)

    return remaining_items, removed_count


def _parse_watch_item(raw_item: Any) -> WatchItem:
    if not isinstance(raw_item, dict):
        raise ValueError("Watchlist item must be a JSON object")

    app_id = raw_item.get("app_id")
    region = raw_item.get("region", "us")
    name = raw_item.get("name")
    target_price_cents = raw_item.get("target_price_cents")

    if not isinstance(app_id, int):
        raise ValueError("Watchlist item field 'app_id' must be an integer")

    if not isinstance(region, str) or not region:
        raise ValueError("Watchlist item field 'region' must be a non-empty string")

    if not isinstance(target_price_cents, int):
        raise ValueError("Watchlist item field 'target_price_cents' must be an integer")

    if name is not None and not isinstance(name, str):
        raise ValueError("Watchlist item field 'name' must be a string")

    return WatchItem(
        app_id=app_id,
        target_price_cents=target_price_cents,
        region=region,
        name=name,
    )
