"""检索评测：Recall@k + MRR。

用法：python -m eval.eval_retrieval
前提：Chroma 索引已建好（python -m app.rag），不需要 LLM key 之外的额外费用。
"""
import json
import sys
from pathlib import Path

from app import rag

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

EVAL_FILE = Path(__file__).resolve().parent.parent / "data" / "eval" / "retrieval_eval.json"
TOP_K = 3


def main() -> None:
    cases = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    hit = 0
    rr_sum = 0.0
    misses = []

    for case in cases:
        hits = rag.retrieve(case["question"], top_k=TOP_K)
        sources = [h["source"] for h in hits]
        expected = case["expected_source"]
        if expected in sources:
            hit += 1
            rr_sum += 1 / (sources.index(expected) + 1)
        else:
            misses.append((case["question"], expected, sources))

    n = len(cases)
    print(f"Recall@{TOP_K}: {hit}/{n} = {hit / n:.1%}")
    print(f"MRR: {rr_sum / n:.3f}")

    if misses:
        print(f"\n未命中的 {len(misses)} 条：")
        for q, exp, got in misses:
            print(f"[FAIL] {q}")
            print(f"   期望《{exp}》| 实得 {got}")


if __name__ == "__main__":
    main()
