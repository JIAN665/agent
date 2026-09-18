import json
import os
import tempfile
import unittest
from pathlib import Path

from core.permissions import (
    create_ticket, resolve_ticket, pending_tickets, log_event, read_recent,
    evaluate,
)
from core.permissions.gate import check


def _fake_tool(name="shell.execute", risk="medium"):
    class FakeTool:
        def __init__(self, name, risk):
            self.name = name
            self.risk_level = risk
    return FakeTool(name, risk)


class PolicyTests(unittest.TestCase):
    def test_hard_block_denied(self):
        d = evaluate("shell.execute", {"command": "format C:"})
        self.assertEqual(d.action, "deny")

    def test_sensitive_keyword_approval(self):
        d = evaluate("shell.execute", {"command": "echo 我的银行卡号 1234567890123456"})
        self.assertEqual(d.action, "approval")
        self.assertEqual(d.risk, "critical")

    def test_normal_command_allowed(self):
        d = evaluate("shell.execute", {"command": "echo hello"})
        self.assertEqual(d.action, "allow")

    def test_gate_returns_dict(self):
        r = check(_fake_tool(), {"command": "echo hi"})
        self.assertIn("action", r)


class ApprovalStoreTests(unittest.TestCase):
    def test_create_and_resolve(self):
        t = create_ticket({"tool": "file.delete", "params": {"path": "x"}}, "critical", "test")
        self.assertEqual(t["status"], "pending")
        resolved = resolve_ticket(t["ticket_id"], True)
        self.assertEqual(resolved["status"], "approved")
        self.assertNotIn(t["ticket_id"], [x["ticket_id"] for x in pending_tickets()])


class AuditTests(unittest.TestCase):
    def test_log_written(self):
        before = len(read_recent(1000))
        log_event("test_event", {"tool": "shell.execute", "action": "allow"})
        after = len(read_recent(1000))
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()