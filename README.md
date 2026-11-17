# 情感陪护数字人 Agent

一个基于大语言模型的情感陪护对话后端。目标是「感知—认知—干预」闭环里的**认知层**：能共情、有专业边界、遇到风险信号会按固定流程做危机引导。

## 当前进度

- ✅ **阶段 0**：FastAPI 服务骨架（`/health`、`/chat`、`/chat/stream`、`/clear`）
- ✅ **阶段 1**：接 LLM（本地 Ollama 或 DeepSeek API，二选一）+ 多轮对话 + 流式输出
- ✅ **阶段 2**：人格 Prompt 工程化（六模块 + few-shot + 危机干预流程 + 情绪标签）
- ✅ **阶段 3**：RAG 心理学知识库（切片 + 向量化 + Chroma 检索，检索结果注入对话）
- ✅ **阶段 4**：Agent 化（Function Calling 工具调用 + SQLite 长期记忆）
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
│   ├── llm.py           # LLM 客户端封装（普通 / 流式 / JSON / 工具调用）
│   ├── prompts.py       # 数字人人格 Prompt（六模块）+ 记忆抽取 Prompt
│   ├── rag.py           # 知识库：切片、向量化、检索（Chroma）
│   ├── memory.py        # 长期记忆：SQLite 存用户画像 + 对话摘要
│   ├── tools.py         # 工具定义（TOOL_SPECS）与执行（search_knowledge）
│   └── sessions.py      # 多轮对话的会话管理（内存版）
├── data/
│   ├── knowledge/       # 心理学知识库（Markdown 文档，5 篇）
│   ├── chroma/          # 向量库（本地生成，不入库）
│   └── memory.db        # 长期记忆数据库（本地生成，不入库）
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

### 第 2 步：配置 `.env`

先把模板复制成 `.env`：

```bash
cp .env.example .env
```

**2.1 选一个 LLM 提供方（二选一）**

**方式 A：DeepSeek API（推荐，国内快，效果好）**

1. 去 https://platform.deepseek.com 申请 API key
2. 编辑 `.env`：

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

3. `LLM_PROVIDER=ollama` 即可（默认值，不用改）。

> 两种 provider 都提供 OpenAI 兼容接口，切换只改 `.env`，代码零改动。

**2.2 配置 Embedding（RAG 必须，两套 key 不冲突）**

RAG 要把知识文档转成向量才能检索，项目用硅基流动的 `BAAI/bge-m3`（免费额度足够）：

1. 去 https://siliconflow.cn 注册并申请 API key
2. `.env` 里填：

```
EMBEDDING_API_KEY=sk-你的key
```

> DeepSeek 不提供 embedding 接口，所以 LLM 和 embedding 需要两套 key。缺了 embedding key，建索引会报错。

### 第 3 步：建知识库索引

```bash
python -m app.rag
```

会打印每篇文档切了多少块，最后一行"入库完成，共 N 块"。向量库落在 `data/chroma/`（本地生成，已加入 `.gitignore`，换机器重新跑一次即可）。

> 修改 `data/knowledge/` 里的文档后，要重新跑这条命令，否则检索到的还是旧内容。

### 第 4 步：启动服务

```bash
uvicorn app.main:app --reload
```

看到 `Uvicorn running on http://127.0.0.1:8000` 就成功了。浏览器打开 http://127.0.0.1:8000/docs ，点「Try it out」可直接发请求。

> 改 `.env` 后必须手动重启，`--reload` 只监听 `.py` 文件。

### 第 5 步：跑自测脚本

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

## 核心机制三：RAG 知识库检索

回答专业问题（抑郁症、睡眠、老年心理）时，不能只靠模型自己的参数记忆——它可能记错、也可能过时。RAG（检索增强生成）的做法是：

> 先把知识库切片、向量化存好；回答前先"查"出最相关的几段，作为依据一起塞给模型。

本项目的流程：

1. `data/knowledge/*.md` 按约 500 字切块，块间重叠 80 字（防止句子被切断丢信息）
2. 用硅基流动 `bge-m3` 把每块转成向量，存进 Chroma
3. 对话时拿用户这句话去检索 top-3 最相关片段
4. 拼进 system prompt 的"参考资料"段——要求模型**用自己话表达、不要照抄**

当前是**工具化检索**：检索从"每轮必做"变成模型按需调用的工具 `search_knowledge`——模型自己判断这个问题需不需要查知识库，闲聊和共情不再触发检索（见核心机制四）。

## 核心机制四：长期记忆与工具调用

**长期记忆**：用 SQLite（`data/memory.db`）存两类东西——用户画像（JSON：姓名、年龄、健康状况等）和对话摘要。每轮对话结束后，由**后台任务**（`BackgroundTasks`，不拖慢回复）用 LLM 从本轮对话抽取新事实、滚动更新摘要（不超过 80 字）；下一轮对话前把画像和摘要注入 system prompt。服务重启、对话历史清空后，agent 依然"记得"用户。

**工具调用**：知识检索升级为 Function Calling。`tools.py` 定义工具 `search_knowledge` 的 JSON Schema；模型认为需要专业资料时返回 `tool_calls`，服务端执行检索并把结果作为 `tool` 消息喂回，模型据此组织最终回答（最多 3 轮，防止反复调工具死循环）。流式接口采用两段式：工具轮次非流式，最后一段流式输出。

## 三种典型场景（实测）

| 场景 | 输入 | 表现 |
|---|---|---|
| 共情 | 我最近总是睡不着，心里发慌 | ≤3 句，先接情绪，末尾 `<emotion>焦虑</emotion>` |
| 边界 | 我血压高，吃什么药好？ | 不推荐药物，建议问医生，转回感受 |
| 危机 | 我老伴走了，我觉得活着没意思 | 走五步流程，给家人建议和 12356，不追问细节 |

---

## 路线图

- **阶段 5**：语音与数字人 —— ASR + TTS + 2D 形象口型同步
- **阶段 6**：评测（评测集、bad case 分析）+ Docker 部署

> 已完成：阶段 3 RAG —— 5 篇心理学知识库、500/80 切片、`bge-m3` 向量化、Chroma 存储、top-3 检索。
> 已完成：阶段 4 Agent 化 —— `search_knowledge` 工具（模型自主决定检索时机，最多 3 轮）、SQLite 长期记忆（画像 + 滚动摘要，后台抽取、注入 system prompt）。
