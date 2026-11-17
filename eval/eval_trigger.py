"""对比实验：工具触发率——知识问题应调 search_knowledge，闲聊不应调。

用法：python -m eval.eval_trigger
注意：每条约一次完整 agent 调用，会消耗少量 API 费用。
"""
import json
import sys
from pathlib import Path

from app import main as app_main
from app import memory, sessions, tools

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

EVAL_FILE = Path(__file__).resolve().parent.parent / "data" / "eval" / "trigger_eval.json"

calls = 0
_orig_run_tool = tools.run_tool


def _counting_run_tool(name: str, arguments: str) -> str:
    global calls
    calls += 1
    return _orig_run_tool(name, arguments)


tools.run_tool = _counting_run_tool


def main() -> None:
    cases = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    stats: dict[str, list[int]] = {}

    for i, case in enumerate(cases):
        sid = f"eval-trigger-{i}"
        before = calls
        app_main._run_agent(sid, case["input"])
        triggered = calls > before

        stats.setdefault(case["kind"], [0, 0])
        stats[case["kind"]][0] += 1
        stats[case["kind"]][1] += triggered

        mark = "调用" if triggered else "未调用"
        print(f"[{case['kind']}] {case['input']} → {mark}")

        sessions.clear(sid)
        memory.clear(sid)

    print("\n== 工具触发率 ==")
    for kind, (total, triggered) in stats.items():
        print(f"{kind}类: {triggered}/{total} = {triggered / total:.0%}")
    print(f"工具总调用次数：{calls}")


if __name__ == "__main__":
    main()
