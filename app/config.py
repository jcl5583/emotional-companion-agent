"""配置：从环境变量 / .env 读取 LLM 相关设置。

支持两种 provider（二选一，靠 LLM_PROVIDER 切换）：
- "ollama"  ：本地模型，完全免费、离线，无需 API key（默认）
- "deepseek"：DeepSeek 官方 API，便宜，需要申请 key

两者都是 OpenAI 兼容接口，所以代码里用的是同一个 openai SDK。
"""
import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# DeepSeek（OpenAI 兼容）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Ollama（本地，OpenAI 兼容接口）
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def resolve() -> tuple[str, str, str]:
    """返回 (base_url, api_key, model)。"""
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
    # ollama：api_key 随便填一个即可，Ollama 本地服务不校验
    return OLLAMA_BASE_URL, "ollama", OLLAMA_MODEL
