"""P2 工具层自检脚本：在项目根目录运行  python tools_selftest.py"""
from __future__ import annotations


def main():
    from core.tools import list_tools, run_tool, handle_model_reply, build_tools_context

    print("=" * 62)
    print("P2 工具层自检")
    print("=" * 62)

    tools = list_tools()
    print(f"\n[1] 已注册工具 ({len(tools)} 个):")
    for t in tools:
        print(f"    - {t.name}  (风险: {t.risk_level})")

    print("\n[2] 普通命令执行（应 ok）:")
    r = run_tool("shell.execute", command="echo hello-tools")
    print(f"    -> {r['status']} | {str(r.get('result'))[:80]}")

    print("\n[3] 敏感命令（应 needs_approval）:")
    r = run_tool("shell.execute", command="echo 我的银行卡号 1234567890123456")
    print(f"    -> {r['status']} | {r.get('ticket', {}).get('risk')} | {r.get('reason')}")

    print("\n[4] 硬黑名单（应 denied）:")
    r = run_tool("shell.execute", command="format C:")
    print(f"    -> {r['status']} | {r.get('reason')}")

    print("\n[5] 旧格式模型回复兼容:")
    r = handle_model_reply('{"tool": "execute_command", "command": "echo old-format"}')
    print(f"    -> {r['status']} | {str(r.get('result'))[:80]}")

    print("\n[6] 纯文本不触发工具:")
    r = handle_model_reply("今天天气不错，随便聊聊")
    print(f"    -> {r['status']}")

    print("\n[7] 工具上下文片段（前 3 行）:")
    for line in build_tools_context().splitlines()[:3]:
        print("    " + line)

    print("\n" + "=" * 62)
    print("若 [2][5][6][7] 正常、[3] 需审批、[4] 被拒绝 → P2 基础层可用。")
    print("=" * 62)


if __name__ == "__main__":
    main()