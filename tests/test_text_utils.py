import unittest

from utils.text_utils import extract_json, looks_like_tool_reply


class TextUtilsTests(unittest.TestCase):
    def test_extract_json(self):
        payload = '{"tool": "search_web", "query": "天气"}'
        result = extract_json(payload)
        self.assertEqual(result["tool"], "search_web")

    def test_tool_reply_detection(self):
        self.assertTrue(looks_like_tool_reply('{"tool": "execute_command", "command": "echo hi"}'))


if __name__ == "__main__":
    unittest.main()
