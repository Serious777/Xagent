"""ariz_flow 单元测试"""
import json
import os
import sys
import tempfile
import unittest

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 使用临时数据库避免污染真实数据
_tmpdir = tempfile.mkdtemp()
os.environ.setdefault("XAGENT_DB", os.path.join(_tmpdir, "test_xagent.db"))
os.environ.setdefault("COMPONENT_DB", os.path.join(_tmpdir, "test_components.db"))


class TestArizSteps(unittest.TestCase):
    """测试 ARIZ 步骤定义"""

    def test_get_step_index(self):
        from ariz_flow import get_step_index
        self.assertEqual(get_step_index("problem"), 0)
        self.assertEqual(get_step_index("solution"), 8)
        self.assertEqual(get_step_index("nonexistent"), -1)

    def test_get_step_label(self):
        from ariz_flow import get_step_label
        self.assertEqual(get_step_label("problem"), "问题识别")
        self.assertEqual(get_step_label("solution"), "生成创新方案")
        self.assertEqual(get_step_label("nonexistent"), "nonexistent")

    def test_build_progress(self):
        from ariz_flow import build_progress
        result = build_progress("contacts")
        self.assertIn("👉 3. 接触关系分析（当前步骤）", result)
        self.assertIn("✅ 1. 问题识别", result)
        self.assertIn("⬜ 4. 功能建模", result)


class TestSessionState(unittest.TestCase):
    """测试会话状态管理（SQLite 持久化）"""

    def setUp(self):
        from ariz_flow import get_session_state, reset_flow, _get_db
        # 使用测试 conv_id
        self.conv_id = "test-unit-001"
        reset_flow(self.conv_id)

    def test_get_session_state_default(self):
        from ariz_flow import get_session_state
        state = get_session_state(self.conv_id)
        self.assertEqual(state["current_step"], "problem")
        self.assertEqual(state["step_results"], {})
        self.assertEqual(state["step_history"], [])

    def test_save_and_get_step_result(self):
        from ariz_flow import save_step_result, get_step_result
        test_data = {"problem_object": "热管理系统", "phenomenon": "温度超标"}
        save_step_result(self.conv_id, "problem", test_data)
        result = get_step_result(self.conv_id, "problem")
        self.assertEqual(result["problem_object"], "热管理系统")
        self.assertEqual(result["phenomenon"], "温度超标")

    def test_advance_step(self):
        from ariz_flow import advance_step, get_session_state
        next_step = advance_step(self.conv_id)
        self.assertEqual(next_step, "components")
        state = get_session_state(self.conv_id)
        self.assertEqual(state["current_step"], "components")
        self.assertEqual(len(state["step_history"]), 1)

    def test_advance_step_last(self):
        from ariz_flow import advance_step, save_step_result
        # 推进到 solution
        for _ in range(8):
            advance_step(self.conv_id)
        # solution 是最后一步，再推进返回 None
        result = advance_step(self.conv_id)
        self.assertIsNone(result)

    def test_reset_flow(self):
        from ariz_flow import reset_flow, save_step_result, advance_step, get_session_state
        save_step_result(self.conv_id, "problem", {"test": True})
        advance_step(self.conv_id)
        reset_flow(self.conv_id)
        state = get_session_state(self.conv_id)
        self.assertEqual(state["current_step"], "problem")
        self.assertEqual(state["step_results"], {})

    def test_persistence_across_connections(self):
        """验证状态持久化：保存后重新读取"""
        from ariz_flow import save_step_result, advance_step, _get_db, _init_ariz_table
        save_step_result(self.conv_id, "problem", {"persist_test": True})
        advance_step(self.conv_id)

        # 重新初始化表（模拟重启）
        _init_ariz_table()

        from ariz_flow import get_session_state
        state = get_session_state(self.conv_id)
        self.assertEqual(state["current_step"], "components")
        self.assertTrue(state["step_results"]["problem"]["persist_test"])


class TestBuildSystemPrompt(unittest.TestCase):
    """测试 system prompt 构建"""

    def test_prompt_contains_progress(self):
        from ariz_flow import build_system_prompt
        prompt = build_system_prompt("problem")
        self.assertIn("ARIZ 流程进度", prompt)
        self.assertIn("问题识别", prompt)

    def test_prompt_contains_step_guide(self):
        from ariz_flow import build_system_prompt
        prompt = build_system_prompt("problem")
        self.assertIn("三步聚焦", prompt)

    def test_prompt_injects_history(self):
        from ariz_flow import build_system_prompt
        state = {
            "step_results": {
                "problem": {"problem_object": "热管理系统", "phenomenon": "温度超标"},
            }
        }
        prompt = build_system_prompt("components", state)
        self.assertIn("已完成的分析步骤", prompt)
        self.assertIn("热管理系统", prompt)


class TestSummarizeStepResult(unittest.TestCase):
    """测试步骤结果摘要"""

    def test_summarize_problem(self):
        from ariz_flow import _summarize_step_result
        result = {"problem_object": "热管理系统", "phenomenon": "温度超标", "goal": "降温"}
        summary = _summarize_step_result("problem", result)
        self.assertIn("热管理系统", summary)
        self.assertIn("温度超标", summary)

    def test_summarize_contacts(self):
        from ariz_flow import _summarize_step_result
        result = {"contacts": [
            {"component_a": "冷却板", "component_b": "导热垫", "contact_type": "热传导"},
        ]}
        summary = _summarize_step_result("contacts", result)
        self.assertIn("冷却板", summary)
        self.assertIn("1个接触关系", summary)

    def test_summarize_unknown_step(self):
        from ariz_flow import _summarize_step_result
        summary = _summarize_step_result("unknown", {"key": "value"})
        self.assertIn("key", summary)


class TestInjectHistory(unittest.TestCase):
    """测试历史结果注入"""

    def test_empty_history(self):
        from ariz_flow import inject_history
        result = inject_history({})
        self.assertEqual(result, "")

    def test_with_history(self):
        from ariz_flow import inject_history
        results = {"problem": {"problem_object": "BMS系统"}}
        text = inject_history(results)
        self.assertIn("已完成的分析步骤", text)
        self.assertIn("BMS系统", text)


if __name__ == "__main__":
    unittest.main()
