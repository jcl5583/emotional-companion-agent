"""LLM 客户端封装。

统一用 openai SDK，因为 DeepSeek 和 Ollama 都提供 OpenAI 兼容的接口，
换模型只需改 .env，代码不用动。
"""
from openai import OpenAI

from . import config

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """懒加载：第一次调用时才真正创建连接。"""
    global _client
    if _client is None:
        base_url, api_key, _ = config.resolve()
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _model() -> str:
    return config.resolve()[2]


def chat(messages: list[dict], temperature: float = 0.8) -> str:
    """非流式：一次性返回完整回复。"""
    resp = _get_client().chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def chat_stream(messages: list[dict], temperature: float = 0.8):
    """流式：逐段产出回复内容（generator）。

    用 `yield` 而不是返回列表，好处是前端能"边生成边显示"。
    """
    resp = _get_client().chat.completions.create(
        model=_model(),
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
