"""多轮对话的会话管理（内存版）。

阶段 1 先用进程内存存对话历史，服务重启会清空。
后续阶段会换成数据库（SQLite/MySQL）或 Redis，并加上"长期记忆"（用户画像）。

这里的核心思想：大模型本身是无状态的，它不记得上一句说了什么，
所以"多轮对话"本质是——把历史消息每次一起重新发给它。
"""

# session_id -> 消息列表 [{"role": "user"/"assistant", "content": "..."}]
_sessions: dict[str, list[dict]] = {}

MAX_MESSAGES = 40  # 最多保留 40 条（约 20 轮），超出裁掉最早的，防止无限增长


def get_history(session_id: str) -> list[dict]:
    """返回该会话的历史（首次访问自动创建空列表）。"""
    return _sessions.setdefault(session_id, [])


def append(session_id: str, role: str, content: str) -> None:
    """往会话里追加一条消息，并裁剪到 MAX_MESSAGES 以内。"""
    history = _sessions.setdefault(session_id, [])
    history.append({"role": role, "content": content})
    if len(history) > MAX_MESSAGES:
        del history[: len(history) - MAX_MESSAGES]


def clear(session_id: str) -> None:
    """清空某个会话。"""
    _sessions.pop(session_id, None)
