import unittest

from memory.chat_history import clear_chat_history, load_chat_history, save_chat_history


class ChatHistoryTests(unittest.TestCase):
    def test_chat_history_round_trip(self):
        messages = [{"role": "user", "content": "hello"}]
        save_chat_history(messages)
        loaded = load_chat_history()
        self.assertEqual(loaded[-1]["content"], "hello")
        clear_chat_history()


if __name__ == "__main__":
    unittest.main()
