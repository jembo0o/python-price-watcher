import unittest

from price_watcher.notifier import TelegramChat, extract_telegram_chats


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


if __name__ == "__main__":
    unittest.main()
