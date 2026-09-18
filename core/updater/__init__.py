"""P5 自我更新管道：她提议 → 真实diff → 你审批 → 测试 → 应用 → 可回滚。"""

from core.updater.propose import propose_update, list_proposals, get_proposal
from core.updater.diff import working_tree_diff, changed_files, summarize_diff
from core.updater.safety import check_safety
from core.updater.staging import run_tests
from core.updater.apply import prepare_proposal, apply_proposal, rollback
from core.updater.history import record_update, list_history

__all__ = [
    "propose_update", "list_proposals", "get_proposal",
    "working_tree_diff", "changed_files", "summarize_diff",
    "check_safety", "run_tests",
    "prepare_proposal", "apply_proposal", "rollback",
    "record_update", "list_history",
]