"""更新管理控制台：查看提案、生成diff、审批应用、回滚。
用法: python scripts/update_console.py
"""
from __future__ import annotations

import sys
from pathlib import Path
# 把项目根目录加入搜索路径（本文件在 scripts/ 下，父目录即项目根）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.updater import (list_proposals, get_proposal, prepare_proposal,
                          apply_proposal, rollback, run_tests, list_history)


def _print_proposal(p):
    print(f"\n[{p['id']}] {p['title']}  状态={p['status']}")
    print(f"    类型: {p['type']}  创建: {p['created_at']:.0f}")
    if p.get("diff_stats"):
        print(f"    概要: {p['diff_stats']['short_summary']}")
        print(f"    文件: {', '.join(p['files'][:10])}")


def main():
    print("=" * 58)
    print("澪玖 · 自我更新管理控制台")
    print("=" * 58)
    while True:
        print("\n[1] 查看所有提案  [2] 准备提案(diff+检查)  [3] 审批应用")
        print("[4] 回滚  [5] 跑测试  [6] 更新历史  [0] 退出")
        choice = input("选择: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            props = list_proposals()
            if not props:
                print("（暂无提案）")
            for p in props:
                _print_proposal(p)
        elif choice == "2":
            pid = input("提案ID: ").strip()
            r = prepare_proposal(pid)
            if r["ok"]:
                print("✓ 已生成 diff：", r["stats"]["short_summary"])
                print("安全:", r["safety"]["message"])
                print("\n--- diff 前 60 行 ---")
                print("\n".join(r["diff"].splitlines()[:60]))
            else:
                print("✗", r["message"])
        elif choice == "3":
            pid = input("提案ID: ").strip()
            r = prepare_proposal(pid)
            if not r["ok"]:
                print("✗", r["message"])
                continue
            print("将应用：", r["stats"]["short_summary"])
            ok = input("确认应用? (y/n): ").strip().lower() == "y"
            r2 = apply_proposal(pid, approved=ok)
            print(("✓ " if r2["ok"] else "✗ ") + r2["message"])
            if not r2["ok"] and r2.get("test_output"):
                print("--- 测试输出尾部 ---")
                print(r2["test_output"][-800:])
        elif choice == "4":
            pid = input("要回滚的提案ID: ").strip()
            r = rollback(pid)
            print(("✓ " if r["ok"] else "✗ ") + r["message"])
        elif choice == "5":
            r = run_tests()
            print("测试", "通过 ✓" if r["passed"] else "失败 ✗")
            print(r["output"][-800:])
        elif choice == "6":
            for h in list_history():
                print(f"{h['ts']:.0f}  {h['pid']}  {h['status']}  tag={h['tag']}  {h.get('title','')}")
        else:
            print("无效选择")


if __name__ == "__main__":
    main()