import unittest

from price_watcher.notifier import (
    TelegramChat,
    TelegramUpdate,
    extract_telegram_chats,
    extract_telegram_messages,
)


class NotifierTests(unittest.TestCase):
    def test_extract_telegram_chats_from_updates(self) -> None:
        updates = [
            {
                "message": {
                    "chat": {
                        "id": 123,
                        "type": "private",
                        "first_name": "Sergej",
                    }
                }
            }
        ]

        self.assertEqual(
            extract_telegram_chats(updates),
            [TelegramChat(chat_id=123, chat_type="private", name="Sergej")],
        )

    def test_extract_telegram_chats_deduplicates_chat_ids(self) -> None:
        updates = [
            {"message": {"chat": {"id": 123, "type": "private"}}},
            {"message": {"chat": {"id": 123, "type": "private"}}},
        ]

        self.assertEqual(
            extract_telegram_chats(updates),
            [TelegramChat(chat_id=123, chat_type="private", name=None)],
        )

    def test_extract_telegram_messages_ignores_non_text_updates(self) -> None:
        updates = [
            {
                "update_id": 10,
                "message": {
                    "chat": {"id": 123, "type": "private"},
                    "text": "/list",
                },
            },
            {
                "update_id": 11,
                "message": {
                    "chat": {"id": 123, "type": "private"},
                    "photo": [],
                },
            },
        ]

        self.assertEqual(
            extract_telegram_messages(updates),
            [TelegramUpdate(update_id=10, chat_id=123, text="/list")],
        )


if __name__ == "__main__":
    unittest.main()
