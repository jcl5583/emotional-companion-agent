"""情感陪护数字人 Agent —— 后端服务入口。

阶段 0 + 1：FastAPI 空服务 + 接 LLM 的多轮对话。
运行：uvicorn app.main:app --reload
"""
import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import llm, memory, rag, sessions
from .prompts import MEMORY_EXTRACT_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

app = FastAPI(title="情感陪护数字人 Agent", version="0.1.0")


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class ClearRequest(BaseModel):
    session_id: str = "default"


def _build_messages(session_id: str, user_text: str) -> list[dict]:
    """拼出消息列表：system（人格 + 长期记忆 + 参考资料） + 历史 + 本轮用户消息。"""
    history = sessions.get_history(session_id)

    # 朴素 RAG：拿用户这句话去知识库查最相关的 3 段
    docs = rag.retrieve(user_text, top_k=3)
    reference = "\n\n".join(f"《{d['source']}》：{d['text']}" for d in docs)

    # 长期记忆：空的时候不拼这一段，省 token 也避免空块让模型困惑
    profile, summary = memory.get(session_id)
    memory_block = ""
    if profile or summary:
        parts = []
        if profile:
            parts.append("已知的用户信息：" + json.dumps(profile, ensure_ascii=False))
        if summary:
            parts.append("过往对话摘要：" + summary)
        memory_block = "\n\n# 关于用户（长期记忆）\n" + "\n".join(parts)

    system = (
        SYSTEM_PROMPT
        + memory_block
        + "\n\n# 参考资料（用你自己的话表达，不要照抄）\n"
        + reference
    )

    return [{"role": "system", "content": system}] + history + [{"role": "user", "content": user_text}]

def _update_memory(session_id: str, user_text: str, reply: str) -> None:
    profile, summary = memory.get(session_id)
    messages = [
        {"role": "system", "content": MEMORY_EXTRACT_PROMPT},
        {"role": "user", "content": (
            f"现有画像：{json.dumps(profile, ensure_ascii=False)}\n"
            f"旧摘要：{summary or '（无）'}\n"
            f"本轮对话：\n用户：{user_text}\n小暖：{reply}"
        )},
    ]
    try:
        result = llm.chat_json(messages)
    except Exception as exc:
        logger.warning("记忆抽取失败（session=%s）：%s", session_id, exc)
        return

    facts = result.get("facts") or {}
    if facts:
        profile.update(facts)
        memory.save_profile(session_id, profile)

    new_summary = (result.get("summary") or "").strip()
    if new_summary:
        memory.save_summary(session_id, new_summary)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest, background: BackgroundTasks):
    """非流式对话：一次性返回完整回复，记忆抽取在响应发出后后台执行。"""
    messages = _build_messages(req.session_id, req.message)
    try:
        reply = llm.chat(messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{exc}") from exc

    sessions.append(req.session_id, "user", req.message)
    sessions.append(req.session_id, "assistant", reply)
    background.add_task(_update_memory, req.session_id, req.message, reply)
    return {"reply": reply}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, background: BackgroundTasks):
    """流式对话：以 SSE 形式逐字返回，前端可实时显示。"""
    messages = _build_messages(req.session_id, req.message)

    def generate():
        full = ""
        try:
            for delta in llm.chat_stream(messages):
                full += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
            return

        sessions.append(req.session_id, "user", req.message)
        sessions.append(req.session_id, "assistant", full)
        background.add_task(_update_memory, req.session_id, req.message, full)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/clear")
def clear(req: ClearRequest):
    sessions.clear(req.session_id)
    memory.clear(req.session_id)
    return {"status": "cleared"}
