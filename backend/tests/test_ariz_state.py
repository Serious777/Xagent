"""ArizState 测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ariz_state import (
    ARIZ_STEPS, ARIZ_STEP_NAMES, ARIZ_STEP_LABELS,
    get_step_index, get_step_label, get_next_step, create_initial_state,
)


def test_ariz_steps_count():
    """验证 ARIZ 有 9 个步骤"""
    assert len(ARIZ_STEPS) == 9


def test_ariz_step_names():
    """验证步骤名称正确"""
    assert ARIZ_STEP_NAMES == [
        "problem", "components", "contacts", "function",
        "structure", "summary", "causal", "keypoint", "solution",
    ]


def test_get_step_index():
    """验证步骤索引查找"""
    assert get_step_index("problem") == 0
    assert get_step_index("solution") == 8
    assert get_step_index("nonexistent") == -1


def test_get_step_label():
    """验证步骤标签查找"""
    assert get_step_label("problem") == "问题识别"
    assert get_step_label("solution") == "生成创新方案"
    assert get_step_label("nonexistent") == "nonexistent"


def test_get_next_step():
    """验证下一步查找"""
    assert get_next_step("problem") == "components"
    assert get_next_step("solution") is None
    assert get_next_step("nonexistent") is None


def test_create_initial_state():
    """验证初始状态创建"""
    state = create_initial_state()
    assert state["current_step"] == "problem"
    assert state["step_results"] == {}
    assert state["messages"] == []
    assert state["error"] is None
