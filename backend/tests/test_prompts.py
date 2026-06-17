"""Prompt 加载器测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_load_prompt_system():
    """验证能加载 system prompt"""
    from prompts import load_prompt

    content = load_prompt("system")
    assert "动力电池" in content
    assert "TRIZ" in content
    assert len(content) > 100


def test_load_prompt_not_found():
    """验证加载不存在的 prompt 抛出异常"""
    import pytest
    from prompts import load_prompt

    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_xyz")


def test_list_prompts():
    """验证能列出所有 prompt"""
    from prompts import list_prompts

    names = list_prompts()
    assert "system" in names
    assert len(names) >= 10  # system + 9 steps


def test_load_all_step_prompts():
    """验证能加载所有 step prompt"""
    from prompts import load_prompt

    steps = [
        "step1_problem", "step2_components", "step3_contacts",
        "step4_function", "step5_structure", "step6_summary",
        "step7_causal", "step8_keypoint", "step9_solution",
    ]
    for name in steps:
        content = load_prompt(name)
        assert len(content) > 50, f"{name} 内容太短"
