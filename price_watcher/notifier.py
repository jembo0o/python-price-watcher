from dataclasses import dataclass
from typing import Any


TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"


@dataclass(frozen=True)
class TelegramChat:
    chat_id: int
    chat_type: str
    name: str | None = None


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
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


def get_telegram_chats(bot_token: str) -> list[TelegramChat]:
    if not bot_token:
        raise ValueError("Telegram bot token is required")

    try:
        import requests

        response = requests.get(
            TELEGRAM_GET_UPDATES_URL.format(token=bot_token),
            timeout=10,
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

    return extract_telegram_chats(updates)


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
