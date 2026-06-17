"""上下文管理模块测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from context_manager import (
    estimate_tokens, estimate_messages_tokens, CONTEXT_RULES,
)
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


def test_estimate_tokens():
    """验证 token 估算"""
    assert estimate_tokens("hello") >= 1
    assert estimate_tokens("你好世界") >= 1
    assert estimate_tokens("") >= 1  # 最小为 1


def test_estimate_messages_tokens():
    """验证消息列表 token 估算"""
    messages = [
        SystemMessage(content="系统提示"),
        HumanMessage(content="用户消息"),
        AIMessage(content="助手回复"),
    ]
    total = estimate_messages_tokens(messages)
    assert total > 0


def test_context_rules_coverage():
    """验证所有步骤都有上下文规则"""
    expected_steps = ["problem", "components", "contacts", "function",
                      "structure", "summary", "causal", "keypoint", "solution"]
    for step in expected_steps:
        assert step in CONTEXT_RULES, f"缺少步骤 {step} 的上下文规则"
        assert "max_messages" in CONTEXT_RULES[step]
        assert "summarize_threshold" in CONTEXT_RULES[step]


def test_context_rules_progression():
    """验证上下文预算随步骤递增"""
    steps = ["problem", "components", "contacts", "function",
             "structure", "summary", "causal", "keypoint", "solution"]
    for i in range(len(steps) - 1):
        curr = CONTEXT_RULES[steps[i]]["max_messages"]
        next_val = CONTEXT_RULES[steps[i + 1]]["max_messages"]
        assert next_val >= curr, f"{steps[i+1]} 的预算应 >= {steps[i]}"


def test_compress_messages_no_compression_needed():
    """验证消息少时不压缩"""
    import asyncio
    from context_manager import compress_messages

    messages = [
        SystemMessage(content="系统提示"),
        HumanMessage(content="用户消息"),
        AIMessage(content="助手回复"),
    ]
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            compress_messages(messages, "problem")
        )
    finally:
        loop.close()
    # 消息少于阈值，不压缩
    assert len(result) == len(messages)
