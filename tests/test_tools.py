import os
import tempfile
import unittest

from core.tools import (
    dispatch, run_tool, handle_model_reply, list_tools, build_tools_context,
)
from core.tools.dispatcher import resolve_approval

BUILTIN_TOOLS = ("shell.execute", "file.read", "file.write", "file.list",
                 "file.delete", "memory.store", "memory.retrieve",
                 "web.search", "file.download")


class RegistryTests(unittest.TestCase):
    def test_builtin_tools_registered(self):
        names = [t.name for t in list_tools()]
        for expected in BUILTIN_TOOLS:
            self.assertIn(expected, names)

    def test_unknown_tool(self):
        r = dispatch({"tool": "no.such.tool", "params": {}})
        self.assertEqual(r["status"], "unknown_tool")

    def test_missing_required_param(self):
        r = dispatch({"tool": "shell.execute", "params": {}})
        self.assertEqual(r["status"], "error")
        self.assertIn("缺少必填参数", r["error"])


class DispatchTests(unittest.TestCase):
    def test_shell_execute_ok(self):
        r = run_tool("shell.execute", command="echo hello-tools")
        self.assertEqual(r["status"], "ok")
        self.assertIn("hello-tools", r["result"])

    def test_file_write_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "note.txt")
            self.assertEqual(run_tool("file.write", path=p, content="你好，澪玖")["status"], "ok")
            r = run_tool("file.read", path=p)
            self.assertEqual(r["status"], "ok")
            self.assertIn("你好，澪玖", r["result"])

    def test_file_delete_needs_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "tmp.txt")
            with open(p, "w") as f:
                f.write("x")
            r = run_tool("file.delete", path=p)
            self.assertEqual(r["status"], "needs_approval")
            self.assertEqual(r["ticket"]["risk"], "critical")

    def test_sensitive_keyword_triggers_approval(self):
        r = run_tool("shell.execute", command="echo 我的银行卡号是 1234567890123456")
        self.assertEqual(r["status"], "needs_approval")

    def test_hard_block_denied(self):
        r = run_tool("shell.execute", command="format C:")
        self.assertEqual(r["status"], "denied")

    def test_approval_resolve_approved(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "del.txt")
            with open(p, "w") as f:
                f.write("x")
            r = run_tool("file.delete", path=p)
            self.assertEqual(r["status"], "needs_approval")
            r2 = resolve_approval(r["ticket"]["ticket_id"], True)
            self.assertEqual(r2["status"], "ok")
            self.assertFalse(os.path.exists(p))


class ModelReplyTests(unittest.TestCase):
    def test_parse_new_format(self):
        r = handle_model_reply('{"tool": "shell.execute", "params": {"command": "echo hi"}, "reasoning": "t"}')
        self.assertEqual(r["status"], "ok")

    def test_parse_old_format(self):
        r = handle_model_reply('{"tool": "execute_command", "command": "echo old"}')
        self.assertEqual(r["status"], "ok")

    def test_plain_text_not_tool(self):
        r = handle_model_reply("今天天气不错，随便聊聊")
        self.assertEqual(r["status"], "not_tool")

    def test_context_contains_tools(self):
        ctx = build_tools_context()
        self.assertIn("shell.execute", ctx)
        self.assertIn("file.read", ctx)


if __name__ == "__main__":
    unittest.main()