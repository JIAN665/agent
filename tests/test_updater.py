import unittest

from core.updater.propose import propose_update, get_proposal, list_proposals
from core.updater.safety import check_safety
from core.updater.diff import summarize_diff


class ProposeTests(unittest.TestCase):
    def test_create_and_get(self):
        p = propose_update("测试更新", "测试描述")
        self.assertEqual(p["status"], "proposed")
        got = get_proposal(p["id"])
        self.assertIsNotNone(got)
        self.assertEqual(got["title"], "测试更新")
        self.assertIn(p["id"], [x["id"] for x in list_proposals()])


class SafetyTests(unittest.TestCase):
    def test_block_immutable(self):
        r = check_safety(["core/permissions/gate.py", "ui/main_window.py"])
        self.assertFalse(r["safe"])
        self.assertEqual(len(r["blocked"]), 1)

    def test_allow_normal(self):
        r = check_safety(["core/tools/new_skill.py", "utils/helper.py"])
        self.assertTrue(r["safe"])


class DiffTests(unittest.TestCase):
    def test_summarize_counts(self):
        diff = "+++ a.py\n--- b.py\n+hello\n+world\n-remove\n@@\n"
        s = summarize_diff(diff, ["a.py", "b.py"])
        self.assertEqual(s["lines_added"], 2)
        self.assertEqual(s["lines_removed"], 1)
        self.assertEqual(s["file_count"], 2)


if __name__ == "__main__":
    unittest.main()