"""工具定义与执行。

TOOL_SPECS 是给模型看的 JSON Schema 说明书（决定它什么时候想调、传什么参数）；
run_tool 是模型"点单"之后真正执行的函数。
"""
import json
import logging

from . import rag

logger = logging.getLogger(__name__)

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "在心理学知识库中检索专业资料。"
                "当用户询问心理健康、抑郁、焦虑、睡眠、老年心理等专业知识时使用；"
                "日常闲聊、情绪陪伴时不要使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要检索的关键词或问题，用简短的陈述句",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def _search_knowledge(query: str) -> str:
    hits = rag.retrieve(query, top_k=3)
    if not hits:
        return "知识库没有检索到相关内容。"
    return "\n\n".join(f"《{h['source']}》：{h['text']}" for h in hits)


def run_tool(name: str, arguments: str) -> str:
    """按工具名分发执行。arguments 是模型返回的 JSON 字符串。"""
    logger.info("tool call: %s %s", name, arguments)
    args = json.loads(arguments or "{}")
    if name == "search_knowledge":
        return _search_knowledge(args.get("query", ""))
    return f"未知工具：{name}"
