"""情感陪护数字人 Agent —— 后端服务入口。

阶段 0 + 1：FastAPI 空服务 + 接 LLM 的多轮对话。
运行：uvicorn app.main:app --reload
"""
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import llm, sessions

app = FastAPI(title="情感陪护数字人 Agent", version="0.1.0")

# 数字人角色设定（阶段 2 会继续打磨成正式的心理学人格）
SYSTEM_PROMPT = (
    "你叫「小暖」，是一位面向老年人的情感陪护数字人。"
    "你的风格：温暖、耐心、有同理心，说话通俗、简短，像家人一样聊天。"
    "你具备心理学常识，能识别对方焦虑、抑郁等情绪，但你不是医生，"
    "遇到明显的自伤或危机信号时，要温和地建议对方联系家人、医生或求助热线。"
)


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class ClearRequest(BaseModel):
    session_id: str = "default"


def _build_messages(session_id: str, user_text: str) -> list[dict]:
    """拼出完整消息列表：system 开头 + 历史 + 本轮用户消息（不修改存储）。"""
    history = sessions.get_history(session_id)
    return (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": user_text}]
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    """非流式对话：一次性返回完整回复。"""
    messages = _build_messages(req.session_id, req.message)
    try:
        reply = llm.chat(messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{exc}") from exc

    sessions.append(req.session_id, "user", req.message)
    sessions.append(req.session_id, "assistant", reply)
    return {"reply": reply}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
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
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/clear")
def clear(req: ClearRequest):
    sessions.clear(req.session_id)
    return {"status": "cleared"}
