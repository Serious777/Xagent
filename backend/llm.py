"""LLM 客户端封装 — 基于 LangChain ChatOpenAI"""
import os
from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """获取 LLM 客户端（单例，流式模式）"""
    return ChatOpenAI(
        model=os.getenv("XIAOMI_MODEL", "mimo-v2.5"),
        base_url=os.getenv("XIAOMI_BASE_URL"),
        api_key=os.getenv("XIAOMI_API_KEY"),
        streaming=True,
        timeout=120,
    )


def get_llm_no_stream() -> ChatOpenAI:
    """获取非流式 LLM 客户端（用于摘要等场景）"""
    return ChatOpenAI(
        model=os.getenv("XIAOMI_MODEL", "mimo-v2.5"),
        base_url=os.getenv("XIAOMI_BASE_URL"),
        api_key=os.getenv("XIAOMI_API_KEY"),
        streaming=False,
        timeout=120,
    )
