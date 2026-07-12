from dataclasses import dataclass
from typing import Any


TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"
TELEGRAM_SET_COMMANDS_URL = "https://api.telegram.org/bot{token}/setMyCommands"


@dataclass(frozen=True)
class TelegramChat:
    chat_id: int
    chat_type: str
    name: str | None = None


@dataclass(frozen=True)
class TelegramUpdate:
    update_id: int
    chat_id: int
    text: str


def send_telegram_message(bot_token: str, chat_id: str | int, text: str) -> None:
    if not bot_token:
        raise ValueError("Telegram bot token is required")

    if not chat_id:
        raise ValueError("Telegram chat ID is required")

    try:
        import requests

        response = requests.post(
            TELEGRAM_SEND_MESSAGE_URL.format(token=bot_token),
            json={
                "chat_id": chat_id,
                "text": text,
            },
            timeout=10,
        )
        response.raise_for_status()
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError("Telegram notification failed") from exc


def get_telegram_updates(
    bot_token: str,
    offset: int | None = None,
    timeout: int = 25,
) -> list[TelegramUpdate]:
    params: dict[str, Any] = {
        "timeout": timeout,
        "allowed_updates": '["message"]',
    }
    if offset is not None:
        params["offset"] = offset

    raw_updates = _fetch_telegram_updates(bot_token, params, timeout + 5)
    return extract_telegram_messages(raw_updates)


def set_telegram_commands(
    bot_token: str,
    commands: list[tuple[str, str]],
) -> None:
    if not bot_token:
        raise ValueError("Telegram bot token is required")

    try:
        import requests

        response = requests.post(
            TELEGRAM_SET_COMMANDS_URL.format(token=bot_token),
            json={
                "commands": [
                    {"command": command, "description": description}
                    for command, description in commands
                ]
            },
            timeout=10,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError("Telegram command setup failed") from exc
    except ValueError as exc:
        raise RuntimeError("Telegram returned invalid JSON") from exc

    if payload.get("ok") is not True:
        raise RuntimeError("Telegram command setup failed")


def get_telegram_chats(bot_token: str) -> list[TelegramChat]:
    updates = _fetch_telegram_updates(bot_token, {}, 10)
    return extract_telegram_chats(updates)


def _fetch_telegram_updates(
    bot_token: str,
    params: dict[str, Any],
    request_timeout: int,
) -> list[Any]:
    if not bot_token:
        raise ValueError("Telegram bot token is required")

    try:
        import requests

        response = requests.get(
            TELEGRAM_GET_UPDATES_URL.format(token=bot_token),
            params=params,
            timeout=request_timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except ImportError as exc:
        raise RuntimeError(
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError("Telegram getUpdates failed") from exc
    except ValueError as exc:
        raise RuntimeError("Telegram returned invalid JSON") from exc

    if payload.get("ok") is not True:
        raise RuntimeError("Telegram getUpdates failed")

    updates = payload.get("result")
    if not isinstance(updates, list):
        raise RuntimeError("Telegram getUpdates returned invalid data")

    return updates


def extract_telegram_messages(updates: list[Any]) -> list[TelegramUpdate]:
    messages: list[TelegramUpdate] = []

    for update in updates:
        if not isinstance(update, dict):
            continue

        update_id = update.get("update_id")
        message = update.get("message")
        if not isinstance(update_id, int) or not isinstance(message, dict):
            continue

        chat = message.get("chat")
        text = message.get("text")
        if not isinstance(chat, dict) or not isinstance(text, str):
            continue

        chat_id = chat.get("id")
        if not isinstance(chat_id, int):
            continue

        messages.append(
            TelegramUpdate(
                update_id=update_id,
                chat_id=chat_id,
                text=text,
            )
        )

    return messages


def extract_telegram_chats(updates: list[Any]) -> list[TelegramChat]:
    chats: list[TelegramChat] = []
    seen_chat_ids: set[int] = set()

    for update in updates:
        if not isinstance(update, dict):
            continue

        message = update.get("message") or update.get("channel_post")
        if not isinstance(message, dict):
            continue

        chat = message.get("chat")
        if not isinstance(chat, dict):
            continue

        chat_id = chat.get("id")
        chat_type = chat.get("type")
        if not isinstance(chat_id, int) or not isinstance(chat_type, str):
            continue

        if chat_id in seen_chat_ids:
            continue

        seen_chat_ids.add(chat_id)
        chats.append(
            TelegramChat(
                chat_id=chat_id,
                chat_type=chat_type,
                name=_extract_chat_name(chat),
            )
        )

    return chats


def _extract_chat_name(chat: dict[str, Any]) -> str | None:
    for key in ("title", "username", "first_name"):
        value = chat.get(key)
        if isinstance(value, str) and value:
            return value

    return None
