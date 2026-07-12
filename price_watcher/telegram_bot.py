from __future__ import annotations

import time
from collections.abc import Callable

from price_watcher.checker import (
    build_steam_store_url,
    format_cents,
    format_check_result,
    format_game_label,
)
from price_watcher.money import parse_price_to_cents
from price_watcher.notifier import (
    TelegramUpdate,
    get_telegram_updates,
    send_telegram_message,
    set_telegram_commands,
)
from price_watcher.regions import normalize_region
from price_watcher.runner import run_watch_once
from price_watcher.service import PriceWatcherService


BOT_COMMANDS = [
    ("search", "Search Steam games by title"),
    ("price", "Show a game's current price"),
    ("add", "Add a game to the watchlist"),
    ("list", "Show the watchlist"),
    ("remove", "Remove a game from the watchlist"),
    ("check", "Check all watched prices now"),
    ("help", "Show command examples"),
]

HELP_TEXT = """Price Watcher commands:

/search Elden Ring
/search region=ua Elden Ring
/price 1245620
/price 1245620 region=eu
/add 29.99 Elden Ring
/add 29.99 region=eu Elden Ring
/list
/remove 1245620
/remove 1245620 region=eu
/check

The default region comes from STEAM_REGION in .env."""

OutputWriter = Callable[[str], None]
Sleeper = Callable[[float], None]
Clock = Callable[[], float]


class TelegramPriceWatcherBot:
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        service: PriceWatcherService,
        default_region: str = "us",
        check_interval_seconds: int = 3600,
        poll_timeout_seconds: int = 25,
        output: OutputWriter = print,
        sleeper: Sleeper = time.sleep,
        clock: Clock = time.monotonic,
    ) -> None:
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID must be set")
        if check_interval_seconds <= 0:
            raise ValueError("CHECK_INTERVAL_SECONDS must be greater than 0")
        if poll_timeout_seconds < 0:
            raise ValueError("Telegram poll timeout must not be negative")

        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.service = service
        self.default_region = normalize_region(default_region)
        self.check_interval_seconds = check_interval_seconds
        self.poll_timeout_seconds = poll_timeout_seconds
        self.output = output
        self.sleeper = sleeper
        self.clock = clock

    def run(self, max_cycles: int | None = None) -> int:
        if max_cycles is not None and max_cycles <= 0:
            raise ValueError("Max cycles must be greater than 0")

        self._register_commands()
        self.output(
            "Telegram bot is running. "
            f"Checking prices every {self.check_interval_seconds} seconds."
        )
        self._run_scheduled_check()

        offset: int | None = None
        next_check_at = self.clock() + self.check_interval_seconds
        completed_cycles = 0

        while max_cycles is None or completed_cycles < max_cycles:
            completed_cycles += 1
            try:
                updates = get_telegram_updates(
                    self.bot_token,
                    offset=offset,
                    timeout=self.poll_timeout_seconds,
                )
            except RuntimeError as exc:
                self.output(f"Telegram polling error: {exc}")
                self.sleeper(5)
                updates = []

            for update in updates:
                offset = update.update_id + 1
                try:
                    self.handle_update(update)
                except RuntimeError as exc:
                    self.output(f"Telegram reply failed: {exc}")

            if self.clock() >= next_check_at:
                self._run_scheduled_check()
                next_check_at = self.clock() + self.check_interval_seconds

        return 0

    def handle_update(self, update: TelegramUpdate) -> None:
        if str(update.chat_id) != self.chat_id:
            self._send_text(update.chat_id, "Access denied.")
            return

        text = update.text.strip()
        if not text.startswith("/"):
            self._send_text(update.chat_id, HELP_TEXT)
            return

        command_parts = text.split(maxsplit=1)
        command_token = command_parts[0]
        raw_arguments = command_parts[1] if len(command_parts) == 2 else ""
        command = command_token.split("@", maxsplit=1)[0].lower()
        arguments = raw_arguments.split()

        try:
            response = self._dispatch_command(command, arguments)
        except (ValueError, RuntimeError) as exc:
            response = f"Error: {exc}"

        self._send_text(update.chat_id, response)

    def _dispatch_command(self, command: str, arguments: list[str]) -> str:
        if command in {"/start", "/help"}:
            return HELP_TEXT

        if command == "/search":
            region, remaining = _extract_region(arguments, self.default_region)
            query = " ".join(remaining).strip()
            if not query:
                raise ValueError("Usage: /search [region=eu] game title")

            results = self.service.search(query, region=region, limit=5)
            if not results:
                return "No games found."

            lines = [f"Search results [{region}]:"]
            for result in results:
                price = result.price or "no price"
                lines.append(
                    f"{format_game_label(result.app_id, result.name)}: {price}"
                )
            return "\n".join(lines)

        if command == "/price":
            region, remaining = _extract_region(arguments, self.default_region)
            if len(remaining) != 1 or not remaining[0].isdigit():
                raise ValueError("Usage: /price APP_ID [region=eu]")

            app_id = int(remaining[0])
            price = self.service.get_price(app_id, region)
            if price is None:
                return f"{app_id} [{region}]: price not found"

            return (
                f"{format_game_label(price.app_id, price.name)} [{region}]: "
                f"{price.formatted}\n{build_steam_store_url(price.app_id)}"
            )

        if command == "/add":
            region, remaining = _extract_region(arguments, self.default_region)
            if len(remaining) < 2:
                raise ValueError(
                    "Usage: /add TARGET_PRICE [region=eu] APP_ID or game title"
                )

            target_price_cents = parse_price_to_cents(remaining[0])
            raw_identifier = " ".join(remaining[1:]).strip()
            identifier: int | str = (
                int(raw_identifier) if raw_identifier.isdigit() else raw_identifier
            )
            item = self.service.add_watch_item(
                identifier=identifier,
                target_price_cents=target_price_cents,
                region=region,
            )
            return (
                f"Saved {format_game_label(item.app_id, item.name)} "
                f"[{item.region}] with target <= "
                f"{format_cents(item.target_price_cents)}\n"
                f"{build_steam_store_url(item.app_id)}"
            )

        if command == "/list":
            if arguments:
                raise ValueError("Usage: /list")

            items = self.service.list_watch_items()
            if not items:
                return "Watchlist is empty."

            lines = ["Watchlist:"]
            for item in items:
                lines.append(
                    f"{format_game_label(item.app_id, item.name)} "
                    f"[{item.region}] target <= "
                    f"{format_cents(item.target_price_cents)}"
                )
            return "\n".join(lines)

        if command == "/remove":
            region, remaining = _extract_optional_region(arguments)
            if len(remaining) != 1 or not remaining[0].isdigit():
                raise ValueError("Usage: /remove APP_ID [region=eu]")

            result = self.service.remove_watch_item(int(remaining[0]), region)
            if result.removed_watch_items == 0:
                return "Watchlist item not found."
            return f"Removed {result.removed_watch_items} watchlist item(s)."

        if command == "/check":
            if arguments:
                raise ValueError("Usage: /check")

            results = self.service.check_watchlist()
            if not results:
                return "Watchlist is empty."
            return "\n".join(format_check_result(result) for result in results)

        return "Unknown command.\n\n" + HELP_TEXT

    def _send_text(self, chat_id: int | str, text: str) -> None:
        for chunk in split_telegram_message(text):
            send_telegram_message(self.bot_token, chat_id, chunk)

    def _register_commands(self) -> None:
        try:
            set_telegram_commands(self.bot_token, BOT_COMMANDS)
        except RuntimeError as exc:
            self.output(f"Could not update Telegram command menu: {exc}")

    def _run_scheduled_check(self) -> None:
        try:
            run_watch_once(
                watchlist_path=self.service.watchlist_path,
                notify=True,
                telegram_bot_token=self.bot_token,
                telegram_chat_id=self.chat_id,
                state_path=self.service.state_path,
                output=self.output,
            )
        except (ValueError, RuntimeError) as exc:
            self.output(f"Scheduled watch check failed: {exc}")


def _extract_region(
    arguments: list[str],
    default_region: str,
) -> tuple[str, list[str]]:
    region, remaining = _extract_region_value(arguments, default_region)
    if region is None:
        raise ValueError("Region must be a non-empty value")
    return region, remaining


def _extract_optional_region(
    arguments: list[str],
) -> tuple[str | None, list[str]]:
    return _extract_region_value(arguments, None)


def _extract_region_value(
    arguments: list[str],
    default_region: str | None,
) -> tuple[str | None, list[str]]:
    region = default_region
    remaining: list[str] = []

    for argument in arguments:
        if argument.lower().startswith("region="):
            raw_region = argument.partition("=")[2]
            region = normalize_region(raw_region)
        else:
            remaining.append(argument)

    return region, remaining


def split_telegram_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0

    for line in text.splitlines():
        added_length = len(line) + (1 if current_lines else 0)
        if current_lines and current_length + added_length > limit:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_length = 0

        if len(line) > limit:
            if current_lines:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_length = 0
            chunks.extend(
                line[index : index + limit]
                for index in range(0, len(line), limit)
            )
            continue

        current_lines.append(line)
        current_length += len(line) + (1 if current_length else 0)

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
