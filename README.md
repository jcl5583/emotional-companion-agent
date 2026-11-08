# 情感陪护数字人 Agent（阶段 0 + 1）

一个基于大语言模型的情感陪护对话后端。当前已完成：

- ✅ FastAPI 服务骨架（`/health`、`/chat`、`/chat/stream`、`/clear`）
- ✅ 接 LLM（本地 Ollama 或 DeepSeek API，二选一）
- ✅ 多轮对话（维护会话历史，支持 ≥10 轮上下文）
- ✅ 流式输出（SSE，前端逐字显示）

> 这是「从零到简历」路线的阶段 0 和阶段 1。后续还要做：RAG 心理学知识库、工具调用（Agent 化）、长期记忆、语音 + 数字人前端、评测与部署。

---

## 目录结构

```
emotional-companion-agent/
├── app/
│   ├── __init__.py      # 包标记
│   ├── main.py          # FastAPI 入口 + 接口
│   ├── config.py        # 读取 .env 配置
│   ├── llm.py           # LLM 客户端封装
│   └── sessions.py      # 多轮对话的会话管理（内存版）
├── test_chat.py         # 自测脚本
├── requirements.txt     # 依赖
├── .env.example         # 配置模板（复制成 .env 使用）
└── .gitignore
```

---

## 第一次跑起来的步骤（照着做）

### 第 1 步：装依赖

在项目目录打开终端（PowerShell / CMD），执行：

```bash
python -m venv .venv
```

激活虚拟环境：

- Windows PowerShell：`.venv\Scripts\Activate.ps1`
- Windows CMD：`.venv\Scripts\activate.bat`

然后装依赖：

```bash
pip install -r requirements.txt
```

### 第 2 步：选一个 LLM 提供方（二选一）

**方式 A：本地 Ollama（推荐，免费离线，先试这个）**

1. 去 https://ollama.com 下载安装 Ollama
2. 安装后拉取一个中文模型（3b 体积小、对硬件友好）：

```bash
ollama pull qwen2.5:3b
```

3. 保持默认配置即可（`LLM_PROVIDER=ollama`）。

**方式 B：DeepSeek API（便宜，需要联网）**

1. 去 https://platform.deepseek.com 注册，申请一个 API key
2. 把 `.env.example` 复制成 `.env`：

```bash
cp .env.example .env
```

3. 编辑 `.env`，改成：

```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的key
```

> 用 Ollama 的话其实不需要 `.env`（默认值就是 ollama）。只有切换 provider 或改模型时才需要建 `.env`。

### 第 3 步：启动服务

```bash
uvicorn app.main:app --reload
```

看到 `Uvicorn running on http://127.0.0.1:8000` 就成功了。

浏览器打开 http://127.0.0.1:8000/docs 可以看到自动生成的接口文档（Swagger），点「Try it out」就能直接测试。

### 第 4 步：跑自测脚本

另开一个终端（保持服务运行），执行：

```bash
python test_chat.py
```

---

## 三个接口

| 接口 | 说明 |
|---|---|
| `GET /health` | 健康检查，返回 `{"status":"ok"}` |
| `POST /chat` | 非流式对话，一次性返回完整回复 |
| `POST /chat/stream` | 流式对话（SSE），逐字返回 |
| `POST /clear` | 清空某个会话 |

### curl 示例

非流式：

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"a1\",\"message\":\"你好，我最近有点睡不着\"}"
```

流式（Windows 用 `curl -N` 看逐字输出）：

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"a1\",\"message\":\"能陪我聊聊天吗\"}"
```

（上面 `^` 是 Windows CMD 的换行符；PowerShell 请用反引号 `` ` ``，或把命令写成一行。）

---

## 核心原理：多轮对话是怎么实现的？

大模型本身是**无状态**的——它不记得上一句。所谓"多轮对话"，本质是：

> 每次把 **system 提示 + 之前所有历史消息 + 本轮新消息** 拼成一个 `messages` 列表，一起发给模型。

所以 `sessions.py` 里做的事就是：用 `session_id` 把每个会话的历史存起来，每次请求都取出来拼上再发。这就是 `app/main.py` 里 `_build_messages()` 干的事。

理解这一点，你就能回答面试题「你的多轮对话是怎么做的」。

---

## 下一步（阶段 2、3）

1. **阶段 2**：把 `SYSTEM_PROMPT` 打磨成完整的心理学人格（共情、专业边界、危机干预话术）
2. **阶段 3**：加 RAG —— 心理学知识库向量化 + 检索，让回答有专业依据
