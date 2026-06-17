"""LLM 客户端测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_get_llm_returns_chatopenai():
    """验证 get_llm 返回 ChatOpenAI 实例"""
    from dotenv import load_dotenv
    load_dotenv()

    from llm import get_llm
    from langchain_openai import ChatOpenAI

    llm = get_llm()
    assert isinstance(llm, ChatOpenAI)


def test_get_llm_singleton():
    """验证 get_llm 返回同一实例"""
    from dotenv import load_dotenv
    load_dotenv()

    from llm import get_llm

    llm1 = get_llm()
    llm2 = get_llm()
    assert llm1 is llm2


def test_get_llm_no_stream():
    """验证 get_llm_no_stream 关闭流式"""
    from dotenv import load_dotenv
    load_dotenv()

    from llm import get_llm_no_stream

    llm = get_llm_no_stream()
    assert llm.streaming is False
