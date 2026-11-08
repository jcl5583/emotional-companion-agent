"""快速自测脚本。

先启动服务：uvicorn app.main:app --reload
再运行本脚本：python test_chat.py
"""
import json

import requests

BASE = "http://127.0.0.1:8000"


def test_health():
    r = requests.get(f"{BASE}/health")
    print("[health]", r.json())


def test_chat():
    r = requests.post(
        f"{BASE}/chat",
        json={"session_id": "test", "message": "你好，我最近有点睡不着"},
    )
    print("[chat]", r.json()["reply"])


def test_stream():
    r = requests.post(
        f"{BASE}/chat/stream",
        json={"session_id": "test", "message": "能陪我聊聊天吗"},
        stream=True,
    )
    print("[stream] ", end="", flush=True)
    for line in r.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            print(json.loads(data)["delta"], end="", flush=True)
    print()


if __name__ == "__main__":
    test_health()
    test_chat()
    test_stream()
