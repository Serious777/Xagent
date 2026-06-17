"""LangGraph ARIZ 流程图测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ariz_graph import build_ariz_graph, route_after_summary
from ariz_state import create_initial_state


def test_build_ariz_graph():
    """验证图构建成功"""
    graph = build_ariz_graph()
    assert graph is not None


def test_graph_has_all_nodes():
    """验证图包含所有 9 个节点"""
    graph = build_ariz_graph()
    node_names = list(graph.nodes)
    expected = ["problem", "components", "contacts", "function",
                "structure", "summary", "causal", "keypoint", "solution"]
    for name in expected:
        assert name in node_names, f"缺少节点: {name}"


def test_route_after_summary_few_problems():
    """验证问题少时跳过因果链"""
    state = create_initial_state()
    state["step_results"] = {
        "summary": {"problems": {"insufficient": ["问题1", "问题2"]}}
    }
    result = route_after_summary(state)
    assert result == "keypoint"


def test_route_after_summary_many_problems():
    """验证问题多时走因果链"""
    state = create_initial_state()
    state["step_results"] = {
        "summary": {"problems": {
            "insufficient": ["问题1", "问题2"],
            "harmful": ["问题3", "问题4"],
        }}
    }
    result = route_after_summary(state)
    assert result == "causal"
