# 情感陪护数字人 Agent

一个基于大语言模型的情感陪护对话后端。目标是「感知—认知—干预」闭环里的**认知层**：能共情、有专业边界、遇到风险信号会按固定流程做危机引导。

## 当前进度

- ✅ **阶段 0**：FastAPI 服务骨架（`/health`、`/chat`、`/chat/stream`、`/clear`）
- ✅ **阶段 1**：接 LLM（本地 Ollama 或 DeepSeek API，二选一）+ 多轮对话 + 流式输出
- ✅ **阶段 2**：人格 Prompt 工程化（六模块 + few-shot + 危机干预流程 + 情绪标签）
- ⬜ 阶段 3：RAG 心理学知识库
- ⬜ 阶段 4：Agent 化（工具调用 + 记忆）
- ⬜ 阶段 5：语音 + 数字人前端
- ⬜ 阶段 6：评测 + 部署 + 简历

---

## 目录结构

```
emotional-companion-agent/
├── app/
│   ├── __init__.py      # 包标记
│   ├── main.py          # FastAPI 入口 + 接口
│   ├── config.py        # 读取 .env 配置，切换 LLM provider
│   ├── llm.py           # LLM 客户端封装（普通 / 流式）
│   ├── prompts.py       # 数字人人格 Prompt（六模块）
│   └── sessions.py      # 多轮对话的会话管理（内存版）
├── test_chat.py         # 自测脚本
├── requirements.txt     # 依赖
├── .env.example         # 配置模板（复制成 .env 使用）
└── .gitignore
```

---

## 快速开始

### 第 1 步：装依赖

在项目目录打开终端（PowerShell / CMD）：

```bash
python -m venv .venv
```

激活虚拟环境：

- Windows PowerShell：`.venv\Scripts\Activate.ps1`
- Windows CMD：`.venv\Scripts\activate.bat`

装依赖：

```bash
pip install -r requirements.txt
```

> 不想激活的话，后续命令可以用 `.venv\Scripts\python.exe -m uvicorn ...` 代替。

### 第 2 步：选一个 LLM 提供方（二选一）

**方式 A：DeepSeek API（推荐，国内快，效果好）**

1. 去 https://platform.deepseek.com 申请 API key
2. 把 `.env.example` 复制成 `.env`：

```bash
cp .env.example .env
```

3. 编辑 `.env`：

```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的key
```

**方式 B：本地 Ollama（免费离线）**

1. 去 https://ollama.com 下载安装
2. 拉模型：

```bash
ollama pull qwen2.5:3b
```

3. 不建 `.env` 即可，默认就走 Ollama。

> 两种 provider 都提供 OpenAI 兼容接口，切换只改 `.env`，代码零改动。

### 第 3 步：启动服务

```bash
uvicorn app.main:app --reload
```

看到 `Uvicorn running on http://127.0.0.1:8000` 就成功了。浏览器打开 http://127.0.0.1:8000/docs ，点「Try it out」可直接发请求。

> 改 `.env` 后必须手动重启，`--reload` 只监听 `.py` 文件。

### 第 4 步：跑自测脚本

另开一个终端（保持服务运行）：

```bash
python test_chat.py
```

---

## 接口

| 接口 | 说明 |
|---|---|
| `GET /health` | 健康检查，返回 `{"status":"ok"}` |
| `POST /chat` | 非流式对话，一次性返回完整回复 |
| `POST /chat/stream` | 流式对话（SSE），逐字返回 |
| `POST /clear` | 清空某个会话 |

### curl 示例（PowerShell 请写成一行）

```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"session_id\":\"a1\",\"message\":\"你好，我最近有点睡不着\"}"
```

---

## 核心机制一：多轮对话

大模型本身是**无状态**的。所谓"多轮对话"，本质是：

> 每次把 **system 提示 + 之前所有历史消息 + 本轮新消息** 拼成一个 `messages` 列表，一起发给模型。

`sessions.py` 用 `session_id` 存每个会话的历史（内存版，服务重启会清空），`main.py` 的 `_build_messages()` 负责拼接。

## 核心机制二：人格 Prompt

`app/prompts.py` 里的 `SYSTEM_PROMPT` 拆成六个模块：

| 模块 | 作用 |
|---|---|
| 身份 | 名字、年龄感、与用户的关系 |
| 目标 | 为谁服务、解决什么 |
| 说话风格 | 句长、语气、称呼、提问频率 |
| 能力边界 | 不做诊断、不推荐药物，医学问题转介医生 |
| 安全与危机 | 自伤/自杀信号的五步固定响应流程 |
| 输出约束 | 正文 ≤3 句，末尾输出 `<emotion>标签</emotion>` |

末尾附两组 few-shot：一组演示共情，一组演示医疗边界拒绝。

**危机处理是写死的流程**，不交给模型自由发挥：

1. 接住情绪，不评判、不说教
2. 明确表达担心
3. 建议联系家人，或拨打全国心理援助热线 **12356**
4. 不提供方法性内容，不追问手段或计划
5. 不结束对话

> ⚠️ 本项目是技术演示，不构成医疗建议，不能替代专业心理干预。

## 三种典型场景（实测）

| 场景 | 输入 | 表现 |
|---|---|---|
| 共情 | 我最近总是睡不着，心里发慌 | ≤3 句，先接情绪，末尾 `<emotion>焦虑</emotion>` |
| 边界 | 我血压高，吃什么药好？ | 不推荐药物，建议问医生，转回感受 |
| 危机 | 我老伴走了，我觉得活着没意思 | 走五步流程，给家人建议和 12356，不追问细节 |

---

## 路线图

- **阶段 3**：RAG —— 心理学知识库切片、向量化、检索，回答有专业依据
- **阶段 4**：Agent 化 —— Function Calling 工具（情绪评估 / 知识检索 / 危机干预）+ 长期记忆
- **阶段 5**：语音与数字人 —— ASR + TTS + 2D 形象口型同步
- **阶段 6**：评测（评测集、bad case 分析）+ Docker 部署
