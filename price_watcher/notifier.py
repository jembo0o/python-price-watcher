TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"


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
