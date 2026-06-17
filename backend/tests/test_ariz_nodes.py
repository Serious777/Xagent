"""ARIZ Node 函数测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ariz_nodes import build_messages_for_step, build_history_context, summarize_step_result
from ariz_state import create_initial_state


def test_build_messages_for_step():
    """验证消息构建"""
    state = create_initial_state()
    messages = build_messages_for_step(state, "problem")
    # 至少有 system prompt + step prompt
    assert len(messages) >= 2
    assert "动力电池" in messages[0].content


def test_build_history_context_empty():
    """验证空历史上下文"""
    result = build_history_context({})
    assert result == ""


def test_build_history_context_with_results():
    """验证有历史结果时的上下文构建"""
    step_results = {
        "problem": {
            "problem_object": "热管理系统",
            "phenomenon": "温度过高",
        }
    }
    result = build_history_context(step_results)
    assert "问题识别" in result
    assert "热管理系统" in result


def test_summarize_step_result_problem():
    """验证 Step 1 结果摘要"""
    result = {
        "problem_object": "热管理系统",
        "phenomenon": "2C放电时温度48°C",
        "goal": "温度≤40°C",
        "constraints": ["不增加重量"],
    }
    summary = summarize_step_result("problem", result)
    assert "热管理系统" in summary
    assert "48°C" in summary


def test_summarize_step_result_contacts():
    """验证 Step 3 结果摘要"""
    result = {
        "contacts": [
            {"component_a": "冷却板", "component_b": "电芯", "contact_type": "热传导"},
        ]
    }
    summary = summarize_step_result("contacts", result)
    assert "冷却板" in summary
    assert "热传导" in summary
