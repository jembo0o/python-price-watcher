import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from price_watcher.watchlist import WatchItem

if TYPE_CHECKING:
    from price_watcher.checker import PriceCheckResult


DEFAULT_STATE_PATH = Path("state.json")


@dataclass(frozen=True)
class NotificationState:
    last_notified_price_cents: int
    target_price_cents: int


def make_state_key(item: WatchItem) -> str:
    return f"{item.app_id}:{item.region}"


def load_notification_state(
    path: Path = DEFAULT_STATE_PATH,
) -> dict[str, NotificationState]:
    if not path.exists():
        return {}

    try:
        raw_state: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid state JSON: {path}") from exc

    if not isinstance(raw_state, dict):
        raise ValueError("State must contain a JSON object")

    return {
        key: _parse_notification_state(value)
        for key, value in raw_state.items()
        if isinstance(key, str)
    }


def save_notification_state(
    state: dict[str, NotificationState],
    path: Path = DEFAULT_STATE_PATH,
) -> None:
    path.write_text(
        json.dumps(
            {key: asdict(value) for key, value in state.items()},
            indent=2,
        ),
        encoding="utf-8",
    )


def filter_notifiable_results(
    results: list["PriceCheckResult"],
    state: dict[str, NotificationState],
) -> list["PriceCheckResult"]:
    return [
        result
        for result in results
        if should_notify_about_result(result, state)
    ]


def should_notify_about_result(
    result: "PriceCheckResult",
    state: dict[str, NotificationState],
) -> bool:
    if not result.is_target_met or result.price is None:
        return False

    previous_state = state.get(make_state_key(result.item))
    if previous_state is None:
        return True

    return result.price.price_cents < previous_state.last_notified_price_cents


def mark_results_as_notified(
    state: dict[str, NotificationState],
    results: list["PriceCheckResult"],
    path: Path = DEFAULT_STATE_PATH,
) -> dict[str, NotificationState]:
    updated_state = dict(state)

    for result in results:
        if result.price is None:
            continue

        updated_state[make_state_key(result.item)] = NotificationState(
            last_notified_price_cents=result.price.price_cents,
            target_price_cents=result.item.target_price_cents,
        )

    save_notification_state(updated_state, path)
    return updated_state


def remove_notification_state(
    app_id: int,
    region: str | None = None,
    path: Path = DEFAULT_STATE_PATH,
) -> tuple[dict[str, NotificationState], int]:
    state = load_notification_state(path)
    updated_state: dict[str, NotificationState] = {}
    removed_count = 0

    for key, value in state.items():
        key_app_id, key_region = _split_state_key(key)
        region_matches = region is None or key_region == region
        if key_app_id == app_id and region_matches:
            removed_count += 1
            continue

        updated_state[key] = value

    if removed_count:
        save_notification_state(updated_state, path)

    return updated_state, removed_count


def _parse_notification_state(raw_value: Any) -> NotificationState:
    if not isinstance(raw_value, dict):
        raise ValueError("State item must be a JSON object")

    last_notified_price_cents = raw_value.get("last_notified_price_cents")
    target_price_cents = raw_value.get("target_price_cents")

    if not isinstance(last_notified_price_cents, int):
        raise ValueError("State field 'last_notified_price_cents' must be an integer")

    if not isinstance(target_price_cents, int):
        raise ValueError("State field 'target_price_cents' must be an integer")

    return NotificationState(
        last_notified_price_cents=last_notified_price_cents,
        target_price_cents=target_price_cents,
    )


def _split_state_key(key: str) -> tuple[int | None, str | None]:
    app_id_text, separator, region = key.partition(":")
    if not separator:
        return None, None

    try:
        return int(app_id_text), region
    except ValueError:
        return None, region
