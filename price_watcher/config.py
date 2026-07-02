import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]
    check_interval_seconds: int
    steam_region: str


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_config() -> Config:
    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        check_interval_seconds=_get_int_env("CHECK_INTERVAL_SECONDS", 3600),
        steam_region=os.getenv("STEAM_REGION", "us"),
    )
